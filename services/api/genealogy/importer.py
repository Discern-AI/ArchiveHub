"""Import a GEDCOM file from a project's Archive into people, relationships and claims.

Every fact becomes a claim (method "import") whose evidence is the file and the GEDCOM
record it came from. Corrections are new claims beside it, never edits (ADR-005).
Re-importing the same file updates rather than duplicates.
"""

from __future__ import annotations

from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from archive.models import Derivative, FileAsset
from archive.processing import JobFailed, decode_text
from history.models import Assertion, AssertionEvidence, LivingStatus, Method, Person

from .gedcom import EVENTS, clean_name, parse, parse_date
from .models import RelationKind, Relationship

PRESUMED_DEAD_AFTER = 110  # years since birth, when no death is recorded


def _text(f: FileAsset) -> str:
    d = Derivative.objects.filter(file=f, kind="text").order_by("created_at").first()
    if d:
        return d.text
    with f.original.open("rb") as fh:
        return decode_text(fh.read())


@transaction.atomic
def import_gedcom(f: FileAsset, user) -> dict:
    records = parse(_text(f))
    people_nodes = [r for r in records if r.tag == "INDI" and r.xref]
    if not people_nodes:
        raise JobFailed("No people were found in this file.")
    project = f.project
    person_type = ContentType.objects.get_for_model(Person)
    this_year = date.today().year
    people: dict[str, Person] = {}
    living = 0

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
        a, _ = Assertion.objects.update_or_create(key=key, defaults=defaults)
        AssertionEvidence.objects.update_or_create(
            assertion=a, file=f, location=f"GEDCOM {xref}",
            defaults={"note": "From the imported family tree file", "stance": "supports"},
        )  # fmt: skip

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
        person, _ = Person.objects.update_or_create(
            project=project, source_file=f, external_id=node.xref,
            defaults={"name": name, "alt_names": alt, "sex": node.text("SEX")[:1].upper(),
                      "living_status": status},
        )  # fmt: skip
        people[node.xref] = person
        claim(person, node.xref, "name", name)
        if node.text("SEX"):
            claim(person, node.xref, "sex", {"M": "Male", "F": "Female"}.get(
                node.text("SEX")[:1].upper(), node.text("SEX")))  # fmt: skip
        for tag, label in EVENTS.items():
            event = node.first(tag)
            if event is None or tag == "MARR":
                continue
            if event.text("DATE"):
                claim(person, node.xref, f"{label} date", event.text("DATE"),
                      parse_date(event.text("DATE")))  # fmt: skip
            if event.text("PLAC"):
                claim(person, node.xref, f"{label} place", event.text("PLAC"))
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
            Relationship.objects.update_or_create(
                project=project, person=a, relative=b, kind=RelationKind.SPOUSE,
                defaults={"source_file": f, "external_id": fam.xref or "", "fields": fields},
            )  # fmt: skip
        for parent in partners:
            for child in children:
                Relationship.objects.update_or_create(
                    project=project, person=parent, relative=child, kind=RelationKind.PARENT,
                    defaults={"source_file": f, "external_id": fam.xref or ""},
                )  # fmt: skip
        families += 1

    f.status = "indexed"
    f.status_detail = f"Imported {len(people)} people. Open Family to see them."
    f.save()
    return {"people": len(people), "families": families, "living_private": living}
