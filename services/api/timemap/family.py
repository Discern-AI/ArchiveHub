"""Family trees on the time map.

Places in a family tree are text ("Newbury, Berkshire, England"). We suggest where each
one is from sources we can name, with a precision, and a person confirms, rejects or
moves it. Births, baptisms, deaths and burials of people who aren't living then appear
as private pins for the project. Living people (including "unknown", ADR-025) never do.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from connectors.base import ConnectorError
from connectors.models import DatasetRow
from connectors.sources import get_connector
from genealogy.exporter import current_values
from history.models import Assertion, LivingStatus, Person, Place

from .models import LocationStatus, PlaceLocation
from .queries import PRIVATE, BBox, MapFeature, overlaps

EVENT_LABELS = ("birth", "baptism", "death", "burial")
# Old map names further apart than this are treated as different places with one name.
SAME_PLACE_KM = 3.0


def text_key(text: str) -> str:
    return " ".join(text.lower().replace(",", " , ").split())


def tree_places(project) -> dict[str, str]:
    """{text_key: text as written} for every event and residence place in the project's trees."""
    ct = ContentType.objects.get_for_model(Person)
    texts = (
        Assertion.objects.filter(
            project=project,
            subject_type=ct,
            predicate__in=[f"{label} place" for label in EVENT_LABELS],
        )
        .values_list("value", flat=True)
        .distinct()
    )
    from genealogy.models import Residence

    texts = [
        *texts,
        *Residence.objects.filter(project=project).values_list("place_text", flat=True),
    ]
    return {text_key(t): t.strip() for t in texts if t.strip()}


def _first_part(text: str) -> str:
    return text.split(",")[0].strip()


def _from_our_places(name: str) -> dict[str, Any] | None:
    p = Place.objects.filter(name__iexact=name, latitude__isnull=False).first()
    if p is None:
        return None
    return {
        "latitude": float(p.latitude),
        "longitude": float(p.longitude),
        "precision": p.geocode_precision,
        "source": p.geocode_source or f"ArchiveHub place: {p}",
        "method": "place",
        "candidates": 1,
    }


def _km(a: DatasetRow, b: DatasetRow) -> float:
    from math import cos, hypot, radians

    dy = (a.latitude - b.latitude) * 111.32
    dx = (a.longitude - b.longitude) * 111.32 * cos(radians(a.latitude))
    return hypot(dx, dy)


def _from_old_map_names(name: str) -> dict[str, Any] | None:
    rows = list(
        DatasetRow.objects.filter(dataset__key="old-map-names", title_lower=name.lower())
        .exclude(latitude__isnull=True)
        .order_by("external_id")[:50]
    )
    if not rows:
        return None
    # Towns and villages are written in capitals on the six-inch map.
    capitals = [r for r in rows if r.title.isupper()] or rows
    first = capitals[0]
    spread = max((_km(first, r) for r in capitals), default=0.0)
    return {
        "latitude": first.latitude,
        "longitude": first.longitude,
        "precision": "town" if first.title.isupper() else "inferred",
        "source": (
            f'Old map names (OS six-inch, c.1900), label "{first.title}" ({first.external_id})'
        ),
        "method": "old-map-names",
        # Several far-apart places share this name: say so, so a person checks it.
        "candidates": len(capitals) if spread > SAME_PLACE_KM else 1,
    }


def _from_geonames(text: str) -> dict[str, Any] | None:
    connector = get_connector("geonames")
    if not connector.configured():
        return None
    try:
        page = connector.search(text, page_size=5)
    except ConnectorError:
        return None
    places = [
        r for r in page.records if r.latitude is not None and r.record_type.startswith("city")
    ]
    if not places:
        return None
    best = places[0]
    return {
        "latitude": best.latitude,
        "longitude": best.longitude,
        "precision": "town",
        "source": f"GeoNames: {best.title}, {best.description} (geonames.org/{best.id})",
        "method": "geonames",
        "candidates": len(places),
    }


def suggest(text: str) -> dict[str, Any] | None:
    """The first source that knows this place. Only the place name is ever sent out."""
    name = _first_part(text)
    if not name:
        return None
    return _from_our_places(name) or _from_old_map_names(name) or _from_geonames(text)


def locate_places(project) -> dict[str, int]:
    """Suggest locations for any place not yet located. People's decisions are kept."""
    found = not_found = 0
    existing = set(PlaceLocation.objects.filter(project=project).values_list("text_key", flat=True))
    for key, text in tree_places(project).items():
        if key in existing:
            continue
        hit = suggest(text)
        if hit:
            PlaceLocation.objects.create(project=project, text=text, text_key=key, **hit)
            found += 1
        else:
            PlaceLocation.objects.create(
                project=project, text=text, text_key=key, status=LocationStatus.NOT_FOUND
            )
            not_found += 1
    return {"suggested": found, "not_found": not_found}


def location_json(loc: PlaceLocation, uses: int = 0) -> dict[str, Any]:
    return {
        "id": str(loc.id),
        "text": loc.text,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "precision": loc.precision,
        "source": loc.source,
        "method": loc.method,
        "candidates": loc.candidates,
        "status": loc.status,
        "uses": uses,
    }


def family_events(user, bbox: BBox, lo, hi, undated, project_titles, project_id=None):
    """Private pins for life events of people in the user's projects who aren't living."""
    locations = PlaceLocation.objects.filter(
        project_id__in=list(project_titles),
        latitude__isnull=False,
        longitude__isnull=False,
    ).exclude(status__in=[LocationStatus.REJECTED, LocationStatus.NOT_FOUND])
    if project_id:
        locations = locations.filter(project_id=project_id)
    locations = [
        loc for loc in locations.filter(bbox.q()) if bbox.contains(loc.latitude, loc.longitude)
    ]
    if not locations:
        return []
    by_project: dict[Any, dict[str, PlaceLocation]] = defaultdict(dict)
    for loc in locations:
        by_project[loc.project_id][loc.text_key] = loc

    out = []
    ct = ContentType.objects.get_for_model(Person)
    for pid, locs in by_project.items():
        place_claims = Assertion.objects.filter(
            project_id=pid,
            subject_type=ct,
            predicate__in=[f"{label} place" for label in EVENT_LABELS],
        )
        wanted = Q()
        for text in {loc.text for loc in locs.values()}:
            wanted |= Q(value__iexact=text)
        person_ids = set(place_claims.filter(wanted).values_list("subject_id", flat=True))
        people = {
            p.id: p
            for p in Person.objects.filter(id__in=person_ids, project_id=pid).exclude(
                living_status__in=[LivingStatus.LIVING, LivingStatus.UNKNOWN]
            )
        }
        if not people:
            continue
        values = current_values(people[next(iter(people))].project, list(people))
        for person_id, person in people.items():
            v = values.get(person_id, {})
            name = v["name"].value if "name" in v else person.name
            for label in EVENT_LABELS:
                place = v.get(f"{label} place")
                if place is None:
                    continue
                loc = locs.get(text_key(place.value))
                if loc is None:
                    continue
                date = v.get(f"{label} date")
                y1 = date.year_from if date else None
                y2 = date.year_to if date else None
                if date is None or (y1 is None and y2 is None):
                    if not undated:
                        continue
                elif not overlaps(y1, y2, lo, hi):
                    continue
                suggested = loc.status == LocationStatus.SUGGESTED
                out.append(
                    MapFeature(
                        id=f"family:{person_id}:{label}",
                        layer=PRIVATE,
                        kind="family_event",
                        title=f"{label.capitalize()} of {name}",
                        summary=f"From the family tree. Place as written: {place.value}.",
                        date_display=date.value if date else "",
                        year_from=y1,
                        year_to=y2,
                        date_role="event" if date else "undated",
                        latitude=loc.latitude,
                        longitude=loc.longitude,
                        precision=loc.precision,
                        place=place.value
                        + (" (location suggested, not yet checked)" if suggested else ""),
                        source=loc.source,
                        link=f"/projects/{pid}/people/{person_id}",
                        project_id=str(pid),
                        project_title=project_titles.get(pid, ""),
                        extra={
                            "person_id": str(person_id),
                            "location_id": str(loc.id),
                            "location_status": loc.status,
                        },  # fmt: skip
                    )
                )
    return out
