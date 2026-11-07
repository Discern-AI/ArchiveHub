"""'What else is known here?' for a spot on the time map, usually a listed building.

Everything comes from evidence we can point to: names written on the c.1900 map close
by, our records and claims for the street the building is on, and (live) Gazette notices
mentioning that street. Nothing here says a record is about this particular building:
our records are placed at street level and modern house numbers may not match old ones.
"""

from __future__ import annotations

import math
from typing import Any

from connectors.base import ConnectorError
from connectors.models import DatasetRow
from connectors.sources import get_connector
from history.glossary import abbreviation
from history.models import Place
from projects.permissions import visible_projects

from .queries import PRIVATE, BBox, _claims, _records

NAME_RADIUS_M = 150
MAX_NAMES = 10


def _metres(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dy = (lat2 - lat1) * 111_320
    dx = (lng2 - lng1) * 111_320 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def _box(lat: float, lng: float, metres: float) -> BBox:
    dlat = metres / 111_320
    dlng = metres / (111_320 * math.cos(math.radians(lat)))
    return BBox(lng - dlng, lat - dlat, lng + dlng, lat + dlat)


def _meaning(title: str) -> dict[str, str]:
    """What an Ordnance Survey abbreviation may mean; several meanings are all given."""
    found = abbreviation(title)
    if not found:
        return {"meaning": "", "meaning_source": ""}
    return {"meaning": found["text"], "meaning_source": found["source_url"]}


def _old_map_names(lat: float, lng: float) -> list[dict[str, Any]]:
    box = _box(lat, lng, NAME_RADIUS_M)
    rows = DatasetRow.objects.filter(dataset__key="old-map-names").filter(box.q())[:200]
    found = [
        {
            "title": r.title,
            "distance_m": round(_metres(lat, lng, r.latitude, r.longitude)),
            **_meaning(r.title),
            "record_id": r.external_id,
            "latitude": r.latitude,
            "longitude": r.longitude,
        }
        for r in rows
        if r.latitude is not None and r.longitude is not None
    ]
    found = [f for f in found if f["distance_m"] <= NAME_RADIUS_M]
    return sorted(found, key=lambda f: f["distance_m"])[:MAX_NAMES]


def _street_named_in(name: str) -> Place | None:
    """A placed street or place whose name appears in the building's name."""
    low = f" {' '.join(name.lower().replace(',', ' ').split())} "
    candidates = Place.objects.select_related("parent").filter(latitude__isnull=False)
    matches = [p for p in candidates if f" {p.name.lower()} " in low]
    return max(matches, key=lambda p: len(p.name), default=None)


def nearby(user, lat: float, lng: float, name: str = "") -> dict[str, Any]:
    notes = []
    names = _old_map_names(lat, lng)
    street = _street_named_in(name) if name else None
    public: list[dict[str, Any]] = []
    private: list[dict[str, Any]] = []
    gazette = None
    if street is not None:
        at = _box(float(street.latitude), float(street.longitude), 5)
        titles = dict(visible_projects(user).values_list("id", "title"))
        for f in _records(at, None, None, True) + _claims(user, at, None, None, True, titles):
            (private if f.layer == PRIVATE else public).append(f.to_dict())
        public.sort(key=lambda f: (f["year_from"] or 99999, f["title"].lower()))
        notes.append(
            f"Records are placed on {street.name} as a whole, so they may be about any "
            "building on it. Modern house numbers may not match old ones."
        )
        gazette = _gazette(street)
    elif name:
        notes.append("No street we hold records for is named in this building's name.")
    return {
        "street": str(street) if street else None,
        "map_names": names,
        "public": public,
        "private": private,
        "gazette": gazette,
        "notes": notes,
    }


def _gazette(street: Place) -> dict[str, Any]:
    """Gazette notices (100+ years old) mentioning the street. Only the street's name is
    sent, which comes from public lists, never from the user."""
    town = street.parent.name if street.parent else ""
    query = f'"{street.name}" {town}'.strip()
    connector = get_connector("the-gazette")
    try:
        page = connector.search(query, page_size=5)
    except ConnectorError as exc:
        return {"searched": f"The Gazette for {query}", "results": [], "error": exc.user_message}
    return {
        "searched": page.searched,
        "results": [
            {
                "id": r.id,
                "title": r.title,
                "snippet": r.description,
                "date": r.date_text,
                "url": r.url,
            }
            for r in page.records
        ],
        "more": bool(page.next_cursor),
        "error": "",
    }
