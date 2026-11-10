"""Export a project's people as GEDCOM 5.5.1, using what the project currently uses for
each fact: its decision if it made one, otherwise the latest correction, otherwise the
imported value. Living people are marked so other software can hide them."""

from __future__ import annotations

import io
import re
import zipfile
from collections import defaultdict
from pathlib import PurePosixPath

from django.contrib.contenttypes.models import ContentType

from archive.models import FileKind, FileStatus
from history.models import Assertion, AssertionEvidence, Decision, LivingStatus, Person

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


_DMY = r"(?:(?:\d{1,2} )?(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC) )?\d{1,4}(?: BCE)?"
GEDCOM7_DATE = re.compile(
    rf"(?:(?:ABT|CAL|EST|BEF|AFT) )?{_DMY}"
    rf"|BET {_DMY} AND {_DMY}"
    rf"|FROM {_DMY}(?: TO {_DMY})?"
    rf"|TO {_DMY}"
)
POINTER_TAGS = {"FAMS", "FAMC", "HUSB", "WIFE", "CHIL", "OBJE"}


def evidence_media(project, people) -> dict:
    """{person_id: [FileAsset]} for files used as evidence for people who have died. Files
    about people who may be living (unknown counts as living) are left out, and so are
    files rejected at upload and imported GEDCOM files (the tree itself, living people
    included)."""
    ct = ContentType.objects.get_for_model(Person)
    dead = [p.id for p in people if p.living_status == LivingStatus.DECEASED]
    out: dict = defaultdict(list)
    rows = (
        AssertionEvidence.objects.filter(
            assertion__project=project,
            assertion__subject_type=ct,
            assertion__subject_id__in=dead,
            file__isnull=False,
            file__project=project,
        )
        .exclude(file__status=FileStatus.REJECTED)
        .exclude(file__kind=FileKind.GEDCOM)
        .select_related("file", "assertion")
        .order_by("file__name")
    )
    for e in rows:
        files = out[e.assertion.subject_id]
        if e.file not in files:
            files.append(e.file)
    return out


def _media_path(f, used: set) -> str:
    """A safe, unique path inside the zip: media/<name>, numbered if names clash."""
    name = PurePosixPath(f.name.replace("\\", "/")).name
    name = "".join(ch if ch.isalnum() or ch in " ._-()" else "_" for ch in name).strip() or "file"
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    path, n = f"media/{name}", 2
    while path in used:
        path = f"media/{stem} ({n}){'.' + ext if ext else ''}"
        n += 1
    used.add(path)
    return path


def export_gedcom(project, version: str = "5.5.1", media: dict | None = None) -> str:
    """The project's tree as GEDCOM 5.5.1 (default) or GEDCOM 7.0, using current values.
    `media` ({person_id: [(path, FileAsset)]}) adds GEDCOM 7 multimedia records."""
    v7 = version == "7.0"
    media = media or {}
    people = list(Person.objects.filter(project=project).order_by("name"))
    ids = {p.id: _x(i, "I") for i, p in enumerate(people, 1)}
    values = current_values(project, list(ids))
    if v7:
        # GEDCOM 7 is UTF-8 only, so there's no CHAR line, and no FORM.
        lines = ["0 HEAD", "1 GEDC", "2 VERS 7.0", "1 SOUR ArchiveHub", "2 NAME ArchiveHub"]
    else:
        lines = ["0 HEAD", "1 SOUR ArchiveHub", "2 NAME ArchiveHub", "1 GEDC", "2 VERS 5.5.1",
                 "2 FORM LINEAGE-LINKED", "1 CHAR UTF-8"]  # fmt: skip

    def add(level: int, tag: str, value: str = "") -> None:
        value = value.replace("\r", "")
        first, *rest = value.split("\n") if value else [""]
        if v7 and first.startswith("@") and tag not in POINTER_TAGS:
            first = "@" + first  # GEDCOM 7: a leading @ in text is doubled
        lines.append(f"{level} {tag} {first}".rstrip())
        lines.extend(f"{level + 1} CONT {r}".rstrip() for r in rest)

    def add_date(level: int, text: str) -> None:
        if not v7:
            add(level, "DATE", text)
            return
        normal = " ".join(text.upper().split())
        if GEDCOM7_DATE.fullmatch(normal):
            add(level, "DATE", normal)
        else:
            # Wording GEDCOM 7 can't parse ("summer 1952") is kept, unchanged, as a phrase.
            add(level, "DATE")
            add(level + 1, "PHRASE", text)

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
    files = {path: f for items in media.values() for path, f in items}
    obje_ids = {path: _x(i, "O") for i, path in enumerate(sorted(files), 1)}

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
                    add_date(2, d.date_text or d.value)
                if pl:
                    add(2, "PLAC", pl.value)
        if p.living_status == LivingStatus.LIVING:
            add(1, "NOTE", "Living person: keep private.")
        for path, _f in media.get(p.id, []):
            add(1, "OBJE", obje_ids[path])
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
    for path, oid in obje_ids.items():
        lines.append(f"0 {oid} OBJE")
        add(1, "FILE", path)
        add(2, "FORM", files[path].content_type.split(";")[0].strip() or "application/octet-stream")
        add(2, "TITL", files[path].name)
    lines.append("0 TRLR")
    return "\n".join(lines) + "\n"


def export_gedzip(project) -> tuple[bytes, int]:
    """GEDCOM 7 GedZip: gedcom.ged plus the evidence files it points to, under media/.
    Returns (zip bytes, number of files included)."""
    people = list(Person.objects.filter(project=project))
    found = evidence_media(project, people)
    # One file can back facts for several people: it gets one path and is stored once.
    used: set = set()
    paths: dict = {}
    for files in found.values():
        for f in files:
            if f.id not in paths:
                paths[f.id] = _media_path(f, used)
    media = {pid: [(paths[f.id], f) for f in files] for pid, files in found.items()}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("gedcom.ged", export_gedcom(project, "7.0", media))
        written = set()
        for items in media.values():
            for path, f in items:
                if path in written:
                    continue
                with f.original.open("rb") as src:
                    z.writestr(path, src.read())
                written.add(path)
    return buf.getvalue(), len(written)
