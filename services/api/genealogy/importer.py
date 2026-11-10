"""Import a GEDCOM file from a project's Archive into people, relationships and claims.

Every fact becomes a claim (method "import") whose evidence is the file and the GEDCOM
record it came from. Corrections are new claims beside it, never edits (ADR-005).

Each imported tree has its own identity ("gedcom:<first file>"). Importing a new export
of the same tree with mode="update" matches people by their ID in that tree (checked
against the name), updates them and adds anyone new; nobody is removed. Re-importing the
same file updates rather than duplicates. Every import is a ChangeSet, so it can be
undone in one step, and preview() shows what an import would do without doing it.
"""

from __future__ import annotations

from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from archive.models import Derivative, FileAsset
from archive.processing import JobFailed, decode_text
from history.models import Assertion, AssertionEvidence, LivingStatus, Method, Person

from .changes import Recorder
from .gedcom import EVENTS, clean_name, parse, parse_date
from .health import check_tree
from .models import ChangeKind, ExternalId, RelationKind, Relationship, Residence
from .report import import_report

PRESUMED_DEAD_AFTER = 110  # years since birth, when no death is recorded


def _text(f: FileAsset) -> str:
    d = Derivative.objects.filter(file=f, kind="text").order_by("created_at").first()
    if d:
        return d.text
    with f.original.open("rb") as fh:
        return decode_text(fh.read())


def tree_system(f: FileAsset) -> str:
    return f"gedcom:{f.id}"


def _tokens(name: str) -> set[str]:
    return {w for w in name.lower().replace("/", " ").split() if len(w) > 1}


def _same_person(old: str, new: str) -> bool:
    """An ID match is only trusted if the names share a word (or one is unnamed)."""
    if "unnamed person" in (old.lower(), new.lower()):
        return True
    return bool(_tokens(old) & _tokens(new))


def _upsert(rec: Recorder, model, lookup: dict, defaults: dict):
    """update_or_create that records what it did, and only touches changed rows."""
    obj = model.objects.filter(**lookup).first()
    if obj is None:
        obj = model.objects.create(**lookup, **defaults)
        rec.created(obj)
        return obj
    changed = {k: v for k, v in defaults.items() if getattr(obj, k) != v}
    if changed:
        rec.before_change(obj)
        for k, v in changed.items():
            setattr(obj, k, v)
        obj.save()
    return obj


class _Rollback(Exception):
    pass


def preview(f: FileAsset, user, mode: str = "new", base: str = "") -> dict:
    """What importing would do, worked out by importing and then rolling it all back."""
    out: dict = {}
    try:
        with transaction.atomic():
            out = import_gedcom(f, user, mode=mode, base=base, save_change=False)
            out["health"] = check_tree(f.project)
            raise _Rollback
    except _Rollback:
        pass
    return out


@transaction.atomic
def import_gedcom(
    f: FileAsset, user, mode: str = "new", base: str = "", save_change: bool = True
) -> dict:
    records = parse(_text(f))
    people_nodes = [r for r in records if r.tag == "INDI" and r.xref]
    if not people_nodes:
        raise JobFailed("No people were found in this file.")
    project = f.project
    updating = mode == "update" and bool(base)
    if updating and not ExternalId.objects.filter(project=project, system=base).exists():
        raise JobFailed("The tree to update wasn't found in this project.")
    system = base if updating else tree_system(f)
    rec = Recorder()
    person_type = ContentType.objects.get_for_model(Person)
    this_year = date.today().year
    people: dict[str, Person] = {}
    living = 0
    added: list[str] = []
    updated: list[str] = []
    id_but_not_name: list[dict[str, str]] = []
    matched: set = set()
    known = {
        e.external_id: e.person
        for e in ExternalId.objects.filter(project=project, system=system).select_related("person")
    }

    def claim(person: Person, xref: str, predicate: str, value: str, gdate=None) -> None:
        key = f"ged-{f.id.hex[:12]}-{xref.strip('@')}-{predicate}"[:100]
        defaults = {
            "subject_type": person_type,
            "subject_id": person.id,
            "predicate": predicate,
            "value": value,
            "status": "documented",
            "method": Method.IMPORT,
            "project": project,
            "created_by": user,
        }
        if gdate:
            defaults.update(date_text=gdate.text, year_from=gdate.year_from,
                            year_to=gdate.year_to, date_precision=gdate.precision)  # fmt: skip
        a = _upsert(rec, Assertion, {"key": key}, defaults)
        _upsert(
            rec,
            AssertionEvidence,
            {"assertion": a, "file": f, "location": f"GEDCOM {xref}"},
            {"note": "From the imported family tree file", "stance": "supports"},
        )

    for node in people_nodes:
        name_node = node.first("NAME")
        name = clean_name(name_node.value) if name_node else ""
        name = name or "Unnamed person"
        alt = [clean_name(n.value) for n in node.all("NAME")[1:] if n.value]
        births = [parse_date(e.text("DATE")) for e in node.all("BIRT") + node.all("CHR")]
        birth_year = next(
            (d.year_from or d.year_to for d in births if d.year_from or d.year_to), None
        )
        died = bool(node.all("DEAT") or node.all("BURI"))
        if died or (birth_year and birth_year < this_year - PRESUMED_DEAD_AFTER):
            status = LivingStatus.DECEASED
        else:
            status = LivingStatus.LIVING  # unknown counts as living: private by default
            living += 1
        fields = {
            "name": name,
            "alt_names": alt,
            "sex": node.text("SEX")[:1].upper(),
            "living_status": status,
        }
        match = known.get(node.xref)
        if match is not None and not _same_person(match.name, name):
            # Same ID but seemingly someone else: nobody is overwritten. Added as new.
            id_but_not_name.append({"id": node.xref, "in_tree": match.name, "in_file": name})
            match = None
        if match is not None:
            person = _upsert(rec, Person, {"pk": match.pk}, fields)
            matched.add(match.pk)
            updated.append(node.xref)
        else:
            person = _upsert(
                rec,
                Person,
                {"project": project, "source_file": f, "external_id": node.xref},
                fields,
            )
            taken = ExternalId.objects.filter(
                project=project, system=system, external_id=node.xref
            ).exists()
            if not taken:
                rec.created(
                    ExternalId.objects.create(
                        project=project, person=person, system=system, external_id=node.xref
                    )
                )
            # If the ID already belongs to someone else, this person is still new; they
            # just can't be matched by that ID next time (the report says so).
            added.append(node.xref)
        people[node.xref] = person
        claim(person, node.xref, "name", name)
        if node.text("SEX"):
            sex = node.text("SEX")[:1].upper()
            claim(person, node.xref, "sex", {"M": "Male", "F": "Female"}.get(sex, sex))
        for tag, label in EVENTS.items():
            event = node.first(tag)
            if event is None or tag == "MARR":
                continue
            if event.text("DATE"):
                claim(person, node.xref, f"{label} date", event.text("DATE"),
                      parse_date(event.text("DATE")))  # fmt: skip
            if event.text("PLAC"):
                claim(person, node.xref, f"{label} place", event.text("PLAC"))
        # Residences come from the latest file: imported ones are replaced; yours stay.
        old = Residence.objects.filter(person=person, method="import")
        if not updating:
            old = old.filter(source_file=f)
        for r in old:
            rec.before_delete(r)
            r.delete()
        for i, resi in enumerate(node.all("RESI"), 1):
            place = resi.text("PLAC") or resi.text("ADDR")
            if not place:
                continue
            when = parse_date(resi.text("DATE")) if resi.text("DATE") else None
            rec.created(
                Residence.objects.create(
                    project=project,
                    person=person,
                    place_text=place[:300],
                    address=resi.text("ADDR")[:300] if resi.text("PLAC") else "",
                    date_text=when.text if when else "",
                    year_from=when.year_from if when else None,
                    year_to=when.year_to if when else None,
                    date_precision=when.precision if when else "unknown",
                    source_file=f,
                    external_id=f"{node.xref} RESI {i}"[:60],
                )
            )
        occupation = node.text("OCCU")
        if occupation:
            claim(person, node.xref, "occupation", occupation)

    families = 0
    for fam in (r for r in records if r.tag == "FAM"):
        partners = [people.get(fam.text(t)) for t in ("HUSB", "WIFE")]
        partners = [p for p in partners if p]
        children = [people.get(c.value.strip()) for c in fam.all("CHIL")]
        children = [c for c in children if c]
        marriage = fam.first("MARR")
        fields = {}
        if marriage is not None:
            fields = {
                "marriage_date": marriage.text("DATE"),
                "marriage_place": marriage.text("PLAC"),
            }
        if len(partners) == 2:
            a, b = partners
            reverse = Relationship.objects.filter(
                project=project, person=b, relative=a, kind=RelationKind.SPOUSE
            ).exists()
            if not reverse:
                _upsert(
                    rec,
                    Relationship,
                    {"project": project, "person": a, "relative": b, "kind": RelationKind.SPOUSE},
                    {"source_file": f, "external_id": fam.xref or "", "fields": fields},
                )
        for parent in partners:
            for child in children:
                _upsert(
                    rec,
                    Relationship,
                    {
                        "project": project,
                        "person": parent,
                        "relative": child,
                        "kind": RelationKind.PARENT,
                    },
                    {"source_file": f, "external_id": fam.xref or ""},
                )
        families += 1

    # People of this tree that nobody in the file matched: kept, and listed.
    not_in_file = sorted(p.name for p in known.values() if p.pk not in matched)
    report = import_report(records)
    f.status = "indexed"
    f.status_detail = f"Imported {len(people)} people. Open Family to see them."
    f.metadata = {**(f.metadata or {}), "import_report": report}
    f.save()
    result = {
        "people": len(people),
        "families": families,
        "living_private": living,
        "report": report,
        "mode": "update" if updating else "new",
        "tree": system,
        "added": len(added),
        "updated": len(updated),
        "not_in_file": not_in_file[:50],
        "not_in_file_count": len(not_in_file),
        "id_but_not_name": id_but_not_name[:50],
    }
    if save_change:
        kind = ChangeKind.UPDATE if updating else ChangeKind.IMPORT
        if updating:
            summary = f"Updated the tree from {f.name}: {len(added)} added, {len(updated)} updated"
        else:
            summary = f"Imported {f.name}: {len(people)} people"
        cs = rec.save(
            project,
            user,
            kind,
            summary,
            {"file_id": str(f.id), "file_name": f.name, "tree": system},
        )
        result["change_set"] = str(cs.id)
        findings = check_tree(project)["findings"]
        kinds = sorted({x["kind"] for x in findings})
        result["health"] = {
            "count": len(findings),
            "by_kind": {k: sum(1 for x in findings if x["kind"] == k) for k in kinds},
        }
    return result
