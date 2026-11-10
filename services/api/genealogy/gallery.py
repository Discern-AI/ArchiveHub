"""Person and family galleries, and suggesting who is in a folder of photos.

A picture is tagged to people with how it relates to them: it shows them, it's about them
(a certificate, a letter), or it shows their world (a street, a workplace). A street scene
is never presented as a photo of someone.

Suggestions come from the file and folder names (a first name, strengthened by the
surname, and years checked against when people were alive) and the camera's date.
They're only suggestions, each with its reason; nothing is tagged until a person
accepts it.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from archive.models import FileAsset, FileKind
from history.models import Person

from .exporter import current_values
from .models import GalleryItem, GalleryTag

YEAR = re.compile(r"(?<!\d)(1[6-9]\d\d|20\d\d)(?!\d)")
WORD = re.compile(r"[a-z]+")


def year_of(text: str) -> int | None:
    m = YEAR.search(text or "")
    return int(m.group(1)) if m else None


def _names(project, people: list[Person]) -> dict:
    values = current_values(project, [p.id for p in people])
    return {
        p.id: (values.get(p.id, {}).get("name").value if "name" in values.get(p.id, {}) else p.name)
        for p in people
    }


def item_json(item: GalleryItem, names: dict, tag: GalleryTag | None = None) -> dict[str, Any]:
    tags = list(item.tags.all())
    return {
        "id": str(item.id),
        "file_id": str(item.file_id),
        "file_name": item.file.name,
        "has_preview": item.file.derivatives.filter(kind="thumbnail").exists(),
        "caption": item.caption,
        "date_text": item.date_text,
        "year": item.year,
        "decade": f"{item.year // 10 * 10}s" if item.year else "Date not known",
        "place_text": item.place_text,
        "relation": tag.relation if tag else None,
        "people": [
            {"id": str(t.person_id), "name": names.get(t.person_id, ""), "relation": t.relation}
            for t in tags
        ],
    }


def person_gallery(project, person: Person) -> list[dict[str, Any]]:
    tags = list(
        GalleryTag.objects.filter(person=person, item__project=project)
        .select_related("item", "item__file")
        .order_by("order", "created_at")
    )
    people = Person.objects.filter(
        pk__in=GalleryTag.objects.filter(item__in=[t.item for t in tags]).values("person_id")
    )
    names = _names(project, list(people))
    return [item_json(t.item, names, t) for t in tags]


def family_gallery(project) -> list[dict[str, Any]]:
    items = list(
        GalleryItem.objects.filter(project=project).select_related("file").prefetch_related("tags")
    )
    people = Person.objects.filter(
        pk__in=GalleryTag.objects.filter(item__in=items).values("person_id")
    )
    names = _names(project, list(people))
    items.sort(key=lambda i: (i.year is None, i.year or 0, i.created_at))
    return [item_json(i, names) for i in items]


def _life(values: dict, pid) -> tuple[int | None, int | None]:
    v = values.get(pid, {})
    b = v.get("birth date") or v.get("baptism date")
    d = v.get("death date") or v.get("burial date")
    born = (b.year_from or b.year_to) if b else None
    died = (d.year_to or d.year_from) if d else None
    return born, died


def suggest_people(project, files: list[FileAsset]) -> list[dict[str, Any]]:
    """For each picture: who it might show, and why. Never tags anyone."""
    people = list(Person.objects.filter(project=project))
    values = current_values(project, [p.id for p in people])
    names = {p.id: (values.get(p.id, {}).get("name").value if "name" in values.get(p.id, {})
                    else p.name) for p in people}  # fmt: skip
    out = []
    for f in files:
        label = f"{f.folder.name if f.folder_id else ''} {f.name.rsplit('.', 1)[0]}"
        words = set(WORD.findall(label.lower().replace("_", " ")))
        when = year_of(label)
        camera = year_of(str((f.metadata or {}).get("camera_date", "")))
        candidates = []
        for p in people:
            parts = [w for w in WORD.findall(names[p.id].lower()) if len(w) > 1]
            if not parts:
                continue
            first, last = parts[0], parts[-1]
            hit_first, hit_last = first in words, last in words and len(parts) > 1
            # A surname alone (often the folder's name) would suggest the whole family:
            # a first name is needed, and the surname makes it stronger.
            if not hit_first:
                continue
            if hit_last:
                score, why = 3, [f"the name says {names[p.id]}"]
            else:
                score, why = 1, [f"the name mentions {first.capitalize()}"]
            born, died = _life(values, p.id)
            year = when or camera
            if year and born and year < born:
                continue  # taken before they were born
            if year and died and year > died + 1:
                continue  # taken after they died
            if year and (born or died):
                why.append(
                    f"they were alive in {year}" if born and (not died or year <= died) else ""
                )
            candidates.append({"id": str(p.id), "name": names[p.id], "score": score,
                               "reason": "; ".join(w for w in why if w)})  # fmt: skip
        candidates.sort(key=lambda c: (-c["score"], c["name"]))
        out.append({
            "file_id": str(f.id),
            "file_name": f.name,
            "folder": f.folder.name if f.folder_id else "",
            "has_preview": f.derivatives.filter(kind="thumbnail").exists(),
            "year_hint": when or camera,
            "year_from": "the file name" if when else "the camera's date" if camera else "",
            "suggestions": candidates[:5],
        })  # fmt: skip
    return out


def unplaced_images(project, folder_id=None) -> list[FileAsset]:
    """Pictures in the Archive not yet in any gallery."""
    placed = GalleryItem.objects.filter(project=project).values("file_id")
    files = FileAsset.objects.filter(project=project, kind=FileKind.IMAGE).exclude(pk__in=placed)
    if folder_id:
        files = files.filter(folder_id=folder_id)
    return list(files.select_related("folder").order_by("folder__name", "name")[:200])


def reorder(person: Person, item_ids: list[str]) -> None:
    by_item = defaultdict(list)
    for t in GalleryTag.objects.filter(person=person):
        by_item[str(t.item_id)].append(t)
    for n, item_id in enumerate(item_ids):
        for t in by_item.get(item_id, []):
            t.order = n
            t.save(update_fields=["order", "updated_at"])
