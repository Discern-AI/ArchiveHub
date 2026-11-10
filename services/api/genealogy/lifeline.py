"""The Lifeline: every person in a tree as a span through time, with where they were
recorded and what was happening around them.

Dates keep their uncertainty. Each end of a life is a window (earliest, latest), so "about
1850" is a few years either side and "before 1900" has no earliest year. The page decides
who was alive in a chosen year from these windows and labels the uncertain ones.

Living people (and anyone whose status isn't known) keep their dates and places private,
as everywhere else: they're listed, not placed in time.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import Q

from history.models import LivingStatus, Person
from timemap.family import text_key
from timemap.models import LocationStatus, PlaceLocation

from .exporter import current_values
from .models import OverlayEvent, OverlayPreset, RelationKind, Relationship, Residence

ABOUT_YEARS = 5  # "about 1850" is read as 1845–1855
START_LABELS = ("birth", "baptism")
END_LABELS = ("death", "burial")
PLACE_LABELS = ("birth", "baptism", "death", "burial")
DEFAULT_KINDS = ["war", "records", "law", "calendar", "family", "custom"]


def window(
    year_from: int | None, year_to: int | None, precision: str, text: str, label: str
) -> dict[str, Any] | None:
    """A date as (earliest, latest), with how sure it is. None if it has no year."""
    if year_from is None and year_to is None:
        return None
    y = year_from if year_from is not None else year_to
    if precision == "approximate":
        earliest, latest, sure = y - ABOUT_YEARS, y + ABOUT_YEARS, "about"
    elif precision == "before":
        earliest, latest, sure = None, year_to if year_to is not None else y, "before"
    elif precision == "after":
        earliest, latest, sure = year_from if year_from is not None else y, None, "after"
    elif precision == "range" or (year_from and year_to and year_from != year_to):
        earliest, latest, sure = year_from, year_to, "range"
    else:
        earliest = latest = y
        sure = "exact"
    # Birth comes before baptism (sometimes years before); death comes just before burial.
    if label == "baptism":
        earliest = earliest - ABOUT_YEARS if earliest is not None else None
        sure = "baptised"
    if label == "burial":
        earliest = earliest - 1 if earliest is not None else None
        sure = "buried"
    return {"earliest": earliest, "latest": latest, "certainty": sure, "text": text,
            "from": label}  # fmt: skip


def _end_of_life(values: dict, labels: tuple[str, ...]) -> dict[str, Any] | None:
    for label in labels:
        a = values.get(f"{label} date")
        if a is None:
            continue
        w = window(a.year_from, a.year_to, a.date_precision, a.date_text or a.value, label)
        if w:
            return w
    return None


def _locations(project) -> dict[str, PlaceLocation]:
    locs = PlaceLocation.objects.filter(
        project=project, latitude__isnull=False, longitude__isnull=False
    ).exclude(status__in=[LocationStatus.REJECTED, LocationStatus.NOT_FOUND])
    return {loc.text_key: loc for loc in locs}


def _place(text: str, locs: dict[str, PlaceLocation]) -> dict[str, Any]:
    loc = locs.get(text_key(text))
    if loc is None:
        return {"place": text, "latitude": None, "longitude": None, "located": "not yet"}
    return {
        "place": text,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "located": "suggested" if loc.status == LocationStatus.SUGGESTED else "checked",
    }


def lifeline(project, user) -> dict[str, Any]:
    people = list(Person.objects.filter(project=project).order_by("name"))
    values = current_values(project, [p.id for p in people])
    locs = _locations(project)
    residences: dict[Any, list[Residence]] = {}
    for r in Residence.objects.filter(project=project):
        residences.setdefault(r.person_id, []).append(r)
    parents: dict[str, list[str]] = {}
    partners: dict[str, list[str]] = {}
    for rel in Relationship.objects.filter(project=project):
        if rel.kind == RelationKind.PARENT:
            parents.setdefault(str(rel.relative_id), []).append(str(rel.person_id))
        else:
            partners.setdefault(str(rel.person_id), []).append(str(rel.relative_id))
            partners.setdefault(str(rel.relative_id), []).append(str(rel.person_id))

    rows, living = [], 0
    for p in people:
        v = values.get(p.id, {})
        name = v["name"].value if "name" in v else p.name
        private = p.living_status != LivingStatus.DECEASED
        row: dict[str, Any] = {
            "id": str(p.id),
            "name": name,
            "surname": name.split()[-1] if name.split() else "",
            "sex": p.sex,
            "living": private,
            "parents": parents.get(str(p.id), []),
            "partners": partners.get(str(p.id), []),
            "start": None,
            "end": None,
            "places": [],
        }
        if private:
            living += 1
            rows.append(row)
            continue
        row["start"] = _end_of_life(v, START_LABELS)
        row["end"] = _end_of_life(v, END_LABELS)
        places = []
        for label in PLACE_LABELS:
            a = v.get(f"{label} place")
            if a is None:
                continue
            d = v.get(f"{label} date")
            places.append({
                "kind": label,
                **_place(a.value, locs),
                "year_from": d.year_from if d else None,
                "year_to": d.year_to if d else None,
                "date_text": (d.date_text or d.value) if d else "",
            })  # fmt: skip
        for r in residences.get(p.id, []):
            places.append({
                "kind": "residence",
                **_place(r.place_text, locs),
                "year_from": r.year_from,
                "year_to": r.year_to,
                "date_text": r.date_text,
            })  # fmt: skip
        places.sort(key=lambda x: x["year_from"] or x["year_to"] or 99999)
        row["places"] = places
        rows.append(row)

    overlays = [
        {
            "id": str(o.id),
            "kind": o.kind,
            "title": o.title,
            "year_from": o.year_from,
            "year_to": o.year_to,
            "date_text": o.date_text,
            "area": o.area,
            "note": o.note,
            "source_title": o.source_title,
            "source_url": o.source_url,
            "builtin": o.project_id is None,
        }
        for o in OverlayEvent.objects.filter(Q(project=None) | Q(project=project))
    ]
    preset = OverlayPreset.objects.filter(project=project, user=user).first()
    return {
        "people": rows,
        "overlays": overlays,
        "kinds": preset.kinds if preset else DEFAULT_KINDS,
        "living_private": living,
        "this_year": date.today().year,
        "about_years": ABOUT_YEARS,
    }
