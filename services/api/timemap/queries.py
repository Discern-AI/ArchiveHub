"""What the time map shows, and to whom. All visibility rules for the map live here.

Public layer: shared reference records, shared claims and events tied to a placed
location, plus old map names for c.1900. Private layer: map items and project claims
from projects the user can see. Every item says which layer it is in, so the two are
never mixed up on screen (SPEC §5).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from connectors.models import DatasetRow
from history.models import Assertion, Event, Organisation, Place, SourceRecord
from history.queries import visible_assertions
from projects.permissions import visible_projects

from .models import MapItem

# The OS six-inch survey the old map names come from (ADR-021).
MAP_NAMES_YEARS = (1888, 1913)
MAP_NAMES_DATASET = "old-map-names"
MAP_NAMES_LIMIT = 300
# Old map names are only listed for an area about the size of a town centre.
MAP_NAMES_MAX_SPAN = 0.08

PUBLIC, PRIVATE = "public", "private"
# Claims whose date is when something was made, not when something happened.
MADE_PREDICATES = {"photographed", "painted", "drawn", "filmed"}


@dataclass
class BBox:
    west: float
    south: float
    east: float
    north: float

    @classmethod
    def parse(cls, text: str) -> BBox:
        parts = [float(p) for p in text.split(",")]
        if len(parts) != 4:
            raise ValueError("bbox needs west,south,east,north")
        west, south, east, north = parts
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError("bbox is out of range")
        return cls(west, south, east, north)

    def contains(self, lat: float | None, lng: float | None) -> bool:
        if lat is None or lng is None:
            return False
        return self.south <= float(lat) <= self.north and self.west <= float(lng) <= self.east

    def q(self, lat: str = "latitude", lng: str = "longitude") -> Q:
        return Q(
            **{
                f"{lat}__gte": self.south,
                f"{lat}__lte": self.north,
                f"{lng}__gte": self.west,
                f"{lng}__lte": self.east,
            }
        )

    @property
    def small(self) -> bool:
        return (self.east - self.west) <= MAP_NAMES_MAX_SPAN and (
            self.north - self.south
        ) <= MAP_NAMES_MAX_SPAN


@dataclass
class MapFeature:
    id: str
    layer: str  # public | private
    kind: str  # record | claim | event | map_name | memory | photo | document | interview
    title: str
    summary: str
    date_display: str
    year_from: int | None
    year_to: int | None
    date_role: str  # event | made | built | record_covers | map_survey | listed | undated
    latitude: float
    longitude: float
    precision: str
    place: str = ""
    source: str = ""
    url: str = ""
    link: str = ""
    project_id: str | None = None
    project_title: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def overlaps(year_from: int | None, year_to: int | None, lo: int | None, hi: int | None) -> bool:
    """Does a dated thing fall in the chosen years? Undated things never match a year."""
    if lo is None and hi is None:
        return True
    start = year_from if year_from is not None else year_to
    end = year_to if year_to is not None else year_from
    if start is None:
        return False
    return (hi is None or start <= hi) and (lo is None or end >= lo)


def _coords(place: Place | None) -> tuple[float, float] | None:
    if place is None or place.latitude is None or place.longitude is None:
        return None
    return float(place.latitude), float(place.longitude)


def _year_filter(qs, lo: int | None, hi: int | None, undated: bool):
    dated = Q(year_from__isnull=False) | Q(year_to__isnull=False)
    if lo is None and hi is None:
        return qs if undated else qs.filter(dated)
    q = dated
    if hi is not None:
        q &= Q(year_from__lte=hi) | Q(year_from__isnull=True, year_to__lte=hi)
    if lo is not None:
        q &= Q(year_to__gte=lo) | Q(year_to__isnull=True, year_from__gte=lo)
    if undated:
        q |= Q(year_from__isnull=True, year_to__isnull=True)
    return qs.filter(q)


def _records(bbox: BBox, lo, hi, undated) -> list[MapFeature]:
    out = []
    qs = SourceRecord.objects.select_related("source", "place").filter(place__isnull=False)
    for r in _year_filter(qs, lo, hi, undated):
        at = _coords(r.place)
        if not at or not bbox.contains(*at):
            continue
        out.append(
            MapFeature(
                id=f"record:{r.key}",
                layer=PUBLIC,
                kind="record",
                title=r.title,
                summary=r.summary,
                date_display=r.date_display,
                year_from=r.year_from,
                year_to=r.year_to,
                date_role="record_covers" if r.date_display else "undated",
                latitude=at[0],
                longitude=at[1],
                precision=r.place.geocode_precision,
                place=str(r.place),
                source=r.source.name,
                url=r.url,
                extra={
                    "record_type": r.record_type,
                    "connector": "checked-reference",
                    "record_id": r.key,
                },
            )
        )
    return out


def _claim_feature(a: Assertion, subject, place: Place, at, project_titles) -> MapFeature:
    layer = PUBLIC if a.project_id is None else PRIVATE
    return MapFeature(
        id=f"claim:{a.id}",
        layer=layer,
        kind="claim",
        title=f"{subject.name}: {a.predicate} {a.value}",
        summary=a.note,
        date_display=a.date_display,
        year_from=a.year_from,
        year_to=a.year_to,
        date_role=(
            ("made" if a.predicate.lower() in MADE_PREDICATES else "event")
            if a.date_display
            else "undated"
        ),
        latitude=at[0],
        longitude=at[1],
        precision=place.geocode_precision,
        place=str(place),
        source="Claim with evidence" if a.method != "ai" else "Suggested by AI",
        project_id=str(a.project_id) if a.project_id else None,
        project_title=project_titles.get(a.project_id, ""),
        extra={
            "subject_type": subject._meta.model_name,
            "subject_id": str(subject.pk),
            "predicate": a.predicate,
            "status": a.status,
            "method": a.method,
        },
    )


def _claims(user, bbox: BBox, lo, hi, undated, project_titles) -> list[MapFeature]:
    """Claims about pubs, businesses and places (never people) at a placed location."""
    org_ct = ContentType.objects.get_for_model(Organisation)
    place_ct = ContentType.objects.get_for_model(Place)
    qs = visible_assertions(user).filter(subject_type__in=[org_ct, place_ct])
    qs = _year_filter(qs, lo, hi, undated)
    claims = list(qs)
    orgs = Organisation.objects.select_related("place", "place__parent").in_bulk(
        {a.subject_id for a in claims if a.subject_type_id == org_ct.id}
    )
    places = Place.objects.select_related("parent").in_bulk(
        {a.subject_id for a in claims if a.subject_type_id == place_ct.id}
    )
    out = []
    for a in claims:
        if a.subject_type_id == org_ct.id:
            subject = orgs.get(a.subject_id)
            place = subject.place if subject else None
        else:
            subject = place = places.get(a.subject_id)
        at = _coords(place)
        if subject is None or not at or not bbox.contains(*at):
            continue
        out.append(_claim_feature(a, subject, place, at, project_titles))
    return out


def _events(bbox: BBox, lo, hi, undated) -> list[MapFeature]:
    """Shared events. Events naming people are left off until people's privacy is known."""
    out = []
    qs = Event.objects.select_related("place", "place__parent").filter(
        place__isnull=False, people__isnull=True
    )
    for e in _year_filter(qs, lo, hi, undated):
        at = _coords(e.place)
        if not at or not bbox.contains(*at):
            continue
        out.append(
            MapFeature(
                id=f"event:{e.id}",
                layer=PUBLIC,
                kind="event",
                title=str(e),
                summary="",
                date_display=e.date_display,
                year_from=e.year_from,
                year_to=e.year_to,
                date_role="event" if e.date_display else "undated",
                latitude=at[0],
                longitude=at[1],
                precision=e.place.geocode_precision,
                place=str(e.place),
            )
        )
    return out


def _map_names(bbox: BBox, lo, hi) -> tuple[list[MapFeature], str]:
    if not overlaps(*MAP_NAMES_YEARS, lo, hi):
        return [], ""
    if not bbox.small:
        return [], "Zoom in to see names from the c.1900 map."
    rows = DatasetRow.objects.filter(dataset__key=MAP_NAMES_DATASET).filter(bbox.q())
    rows = list(rows.order_by("title_lower")[: MAP_NAMES_LIMIT + 1])
    note = ""
    if len(rows) > MAP_NAMES_LIMIT:
        rows, note = rows[:MAP_NAMES_LIMIT], "Showing the first 300 names here; zoom in for more."
    return [
        MapFeature(
            id=f"name:{r.external_id}",
            layer=PUBLIC,
            kind="map_name",
            title=r.title,
            summary="Name written on the OS six-inch map",
            date_display="c.1888–1913",
            year_from=MAP_NAMES_YEARS[0],
            year_to=MAP_NAMES_YEARS[1],
            date_role="map_survey",
            latitude=r.latitude,
            longitude=r.longitude,
            precision="exact",
            source="Old map names (OS six-inch, c.1900)",
            extra={"connector": "old-map-names", "record_id": r.external_id},
        )
        for r in rows
    ], note


def _items(user, bbox: BBox, lo, hi, undated, project_id) -> list[MapFeature]:
    qs = MapItem.objects.filter(project__in=visible_projects(user)).filter(bbox.q())
    if project_id:
        qs = qs.filter(project_id=project_id)
    qs = _year_filter(qs.select_related("project", "place", "place__parent"), lo, hi, undated)
    return [item_feature(i) for i in qs]


def item_feature(i: MapItem) -> MapFeature:
    if i.file_id:
        link = f"/archive?project={i.project_id}&file={i.file_id}"
    elif i.interview_id:
        link = f"/interviews/{i.interview_id}"
    else:
        link = ""
    return MapFeature(
        id=f"item:{i.id}",
        layer=PRIVATE,
        kind=i.kind,
        title=i.title,
        summary=i.text,
        date_display=i.date_display,
        year_from=i.year_from,
        year_to=i.year_to,
        date_role=i.date_role if i.date_display else "undated",
        latitude=i.latitude,
        longitude=i.longitude,
        precision=i.geocode_precision,
        place=str(i.place) if i.place else i.location_note,
        source="Your project",
        link=link,
        project_id=str(i.project_id),
        project_title=i.project.title,
        extra={
            "item_id": str(i.id),
            "file_id": str(i.file_id) if i.file_id else None,
            "interview_id": str(i.interview_id) if i.interview_id else None,
            "lines": i.lines,
            "location_note": i.location_note,
        },
    )


LISTED_LIMIT = 300
LISTED_CACHE_SECONDS = 24 * 3600  # the Heritage List is updated daily


def _listed_buildings(bbox: BBox) -> tuple[list[MapFeature], list[str]]:
    """Listed buildings standing today across the UK (OGL; Northern Ireland from our copy).

    Shown whatever year is chosen: a listing date isn't a build date, so these aren't
    filtered by year, and the panel says so.
    """
    if not bbox.small:
        return [], ["Zoom in to see listed buildings."]
    from django.core.cache import cache

    from .listed import CREDITS, SOURCES, listed_in

    key = "listed:" + ",".join(f"{v:.3f}" for v in (bbox.west, bbox.south, bbox.east, bbox.north))
    cached = cache.get(key)
    notes: list[str] = []
    if cached is None:
        buildings, more, notes = listed_in(bbox, LISTED_LIMIT)
        cached = {"buildings": buildings, "more": more}
        if not notes:  # don't keep a partial answer
            cache.set(key, cached, LISTED_CACHE_SECONDS)
    features = []
    for b in cached["buildings"]:
        england = b["nation"] == "england"
        built = b.get("built", "")
        role = "listed" if b["listed"] else "built" if built else "undated"
        summary = f"{b['grade']} listed building" if b["grade"] else "Listed building"
        if b.get("ref"):
            summary += f" ({b['ref']})"
        features.append(
            MapFeature(
                id=f"listed:{b['id']}",
                layer=PUBLIC,
                kind="listed_building",
                title=b["title"],
                summary=summary,
                date_display=b["listed"] or built,
                year_from=None,
                year_to=None,
                date_role=role,
                latitude=b["latitude"],
                longitude=b["longitude"],
                precision="exact",
                source=SOURCES[b["nation"]],
                url=b["url"],
                extra={
                    "nation": b["nation"],
                    "credit": CREDITS[b["nation"]],
                    **({"address": b["address"]} if b.get("address") else {}),
                    # England's list has a connector, so its buildings can be saved.
                    **(
                        {"connector": "historic-england", "record_id": b["id"].split(":", 1)[1]}
                        if england
                        else {}
                    ),
                },
            )
        )
    if cached["more"]:
        notes.append(
            f"Showing up to {LISTED_LIMIT} listed buildings from each list; zoom in for more."
        )
    return features, notes


def map_features(
    user,
    bbox: BBox,
    year_from: int | None = None,
    year_to: int | None = None,
    undated: bool = False,
    project_id=None,
    listed: bool = False,
) -> dict[str, Any]:
    project_titles = dict(visible_projects(user).values_list("id", "title"))
    if project_id and project_id not in project_titles:
        project_id = None
    public = _records(bbox, year_from, year_to, undated) + _events(
        bbox, year_from, year_to, undated
    )
    claims = _claims(user, bbox, year_from, year_to, undated, project_titles)
    names, names_note = _map_names(bbox, year_from, year_to)
    private = _items(user, bbox, year_from, year_to, undated, project_id)
    from .family import family_events

    private += family_events(user, bbox, year_from, year_to, undated, project_titles, project_id)
    public += [c for c in claims if c.layer == PUBLIC]
    private += [
        c
        for c in claims
        if c.layer == PRIVATE and (not project_id or c.project_id == str(project_id))
    ]

    def key(f: MapFeature):
        return (f.year_from if f.year_from is not None else 99999, f.title.lower())

    notes = [names_note] if names_note else []
    listed_buildings: list[MapFeature] = []
    if listed:
        listed_buildings, listed_notes = _listed_buildings(bbox)
        notes += listed_notes
    unplaced = Place.objects.filter(
        Q(latitude__isnull=True) | Q(longitude__isnull=True), records__isnull=False
    ).distinct()
    for p in unplaced:
        notes.append(f"{p}: records exist but the place has no map location yet.")
    return {
        "public": [f.to_dict() for f in sorted(public, key=key)],
        "private": [f.to_dict() for f in sorted(private, key=key)],
        "map_names": [f.to_dict() for f in names],
        "listed_buildings": [f.to_dict() for f in listed_buildings],
        "notes": notes,
    }
