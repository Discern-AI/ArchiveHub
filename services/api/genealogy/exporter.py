"""Export a project's people as GEDCOM 5.5.1, using what the project currently uses for
each fact: its decision if it made one, otherwise the latest correction, otherwise the
imported value. Living people are marked so other software can hide them."""

from __future__ import annotations

from collections import defaultdict

from django.contrib.contenttypes.models import ContentType

from history.models import Assertion, Decision, LivingStatus, Person

from .models import RelationKind, Relationship


def current_values(project, person_ids) -> dict:
    """{person_id: {predicate: Assertion}} chosen as described above."""
    ct = ContentType.objects.get_for_model(Person)
    decided = {
        (d.subject_id, d.predicate.lower()): d.chosen
        for d in Decision.objects.filter(project=project, subject_type=ct, chosen__isnull=False)
        .select_related("chosen")
    }  # fmt: skip
    out: dict = defaultdict(dict)
    claims = Assertion.objects.filter(
        project=project, subject_type=ct, subject_id__in=person_ids
    ).order_by("created_at")
    for a in claims:
        key = (a.subject_id, a.predicate.lower())
        if key in decided:
            out[a.subject_id][a.predicate.lower()] = decided[key]
            continue
        existing = out[a.subject_id].get(a.predicate.lower())
        # A person's own correction wins over an import; newer corrections win.
        if existing is None or a.method == "user" or existing.method != "user":
            out[a.subject_id][a.predicate.lower()] = a
    return out


def _x(n: int, prefix: str) -> str:
    return f"@{prefix}{n}@"


def export_gedcom(project) -> str:
    people = list(Person.objects.filter(project=project).order_by("name"))
    ids = {p.id: _x(i, "I") for i, p in enumerate(people, 1)}
    values = current_values(project, list(ids))
    lines = ["0 HEAD", "1 SOUR ArchiveHub", "2 NAME ArchiveHub", "1 GEDC", "2 VERS 5.5.1",
             "2 FORM LINEAGE-LINKED", "1 CHAR UTF-8"]  # fmt: skip

    def add(level: int, tag: str, value: str = "") -> None:
        value = value.replace("\r", "")
        first, *rest = value.split("\n") if value else [""]
        lines.append(f"{level} {tag} {first}".rstrip())
        lines.extend(f"{level + 1} CONT {r}".rstrip() for r in rest)

    couples: dict[frozenset, set] = defaultdict(set)
    rels = Relationship.objects.filter(project=project)
    parents_of: dict = defaultdict(set)
    for r in rels:
        if r.kind == RelationKind.SPOUSE:
            couples.setdefault(frozenset({r.person_id, r.relative_id}), set())
        else:
            parents_of[r.relative_id].add(r.person_id)
    for child, parents in parents_of.items():
        couples[frozenset(parents)].add(child)
    fam_ids = {c: _x(i, "F") for i, c in enumerate(couples, 1)}

    for p in people:
        v = values.get(p.id, {})
        lines.append(f"0 {ids[p.id]} INDI")
        name = v["name"].value if "name" in v else p.name
        parts = name.rsplit(" ", 1)
        add(1, "NAME", f"{parts[0]} /{parts[1]}/" if len(parts) == 2 else name)
        if p.sex in ("M", "F"):
            add(1, "SEX", p.sex)
        if "occupation" in v:
            add(1, "OCCU", v["occupation"].value)
        for tag, label in (
            ("BIRT", "birth"),
            ("CHR", "baptism"),
            ("DEAT", "death"),
            ("BURI", "burial"),
        ):
            d, pl = v.get(f"{label} date"), v.get(f"{label} place")
            if d or pl:
                add(1, tag)
                if d:
                    add(2, "DATE", d.date_text or d.value)
                if pl:
                    add(2, "PLAC", pl.value)
        if p.living_status == LivingStatus.LIVING:
            add(1, "NOTE", "Living person: keep private.")
        for couple, fid in fam_ids.items():
            if p.id in couple:
                add(1, "FAMS", fid)
        for couple, fid in fam_ids.items():
            if p.id in couples[couple]:
                add(1, "FAMC", fid)

    by_id = {p.id: p for p in people}
    for couple, fid in fam_ids.items():
        lines.append(f"0 {fid} FAM")
        for pid in sorted(couple, key=str):
            role = "WIFE" if by_id[pid].sex == "F" else "HUSB"
            add(1, role, ids[pid])
        for child in sorted(couples[couple], key=str):
            add(1, "CHIL", ids[child])
    lines.append("0 TRLR")
    return "\n".join(lines) + "\n"
