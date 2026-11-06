"""Time map: layers, what's on the map for a place and years, and a project's own items."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from archive.models import FileAsset, FileKind
from core.models import audit
from history.models import DatePrecision, Place
from interviews.models import InterviewSession
from projects.permissions import editable_projects, visible_projects

from .models import ItemKind, MapItem
from .queries import BBox, item_feature, map_features

router = Router()

NLS_ATTRIBUTION = (
    'Historic map: <a href="https://maps.nls.uk/">National Library of Scotland</a> '
    '(<a href="https://creativecommons.org/licenses/by/3.0/">CC BY 3.0</a>)'
)

# Historic OS layers from the National Library of Scotland, served by MapTiler (ADR-031).
HISTORIC_LAYERS = [
    {
        "id": "os-six-inch-1888",
        "tileset": "uk-osgb10k1888",
        "title": "OS six-inch, 1888–1913",
        "years": [1888, 1913],
        "min_zoom": 10,
    },
    {
        "id": "os-1920s-1940s",
        "tileset": "uk-osgb1919",
        "title": "OS one-inch and smaller, 1920s–1940s",
        "years": [1919, 1947],
        "min_zoom": 6,
    },
    {
        "id": "os-25k-1937",
        "tileset": "uk-osgb25k1937",
        "title": "OS 1:25,000 provisional, 1937–1961",
        "years": [1937, 1961],
        "min_zoom": 10,
    },
]

# Starting points for the pilot (SPEC §5: start with Cheap Street and central Newbury).
START_PLACES = ["cheap-street", "newbury"]


@router.get("/map/layers")
def layers(request: HttpRequest) -> dict[str, Any]:
    key = settings.MAPTILER_KEY
    historic = []
    for layer in HISTORIC_LAYERS:
        entry = {k: v for k, v in layer.items() if k != "tileset"}
        entry["attribution"] = NLS_ATTRIBUTION
        if key:
            entry["available"] = True
            entry["tilejson"] = (
                f"https://api.maptiler.com/tiles/{layer['tileset']}/tiles.json?key={key}"
            )
        else:
            entry["available"] = False
            entry["unavailable_reason"] = "Historic maps aren't set up on this server yet."
        historic.append(entry)
    return {
        "today": {
            "title": "Today",
            "style": settings.MAP_STYLE_URL,
            "attribution": "© OpenMapTiles, data © OpenStreetMap contributors",
        },
        "historic": historic,
    }


def _place_json(p: Place) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "key": p.key,
        "name": str(p),
        "kind": p.kind,
        "latitude": float(p.latitude) if p.latitude is not None else None,
        "longitude": float(p.longitude) if p.longitude is not None else None,
        "precision": p.geocode_precision,
        "geocode_source": p.geocode_source,
        "note": p.note,
    }


@router.get("/map/places")
def places(request: HttpRequest, q: str = "") -> list[dict[str, Any]]:
    """Places with a map location. Without a query, the pilot's starting places first."""
    qs = Place.objects.select_related("parent").filter(latitude__isnull=False)
    if q.strip():
        qs = qs.filter(name__icontains=q.strip()[:100])
    found = list(qs.order_by("name")[:20])
    found.sort(key=lambda p: START_PLACES.index(p.key) if p.key in START_PLACES else 99)
    return [_place_json(p) for p in found]


def _year(value: int | None) -> int | None:
    if value is not None and not -3000 <= value <= 2100:
        raise HttpError(422, "That year is out of range.")
    return value


@router.get("/map/features")
def features(
    request: HttpRequest,
    bbox: str,
    year_from: int | None = None,
    year_to: int | None = None,
    undated: bool = False,
    project_id: UUID | None = None,
) -> dict[str, Any]:
    try:
        box = BBox.parse(bbox)
    except ValueError as exc:
        raise HttpError(422, "The map area wasn't understood.") from exc
    lo, hi = _year(year_from), _year(year_to)
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo
    return map_features(request.user, box, lo, hi, undated, project_id)


# --- A project's own items ------------------------------------------------------------


class ItemIn(Schema):
    kind: Literal["memory", "photo", "document", "interview"]
    title: str
    text: str = ""
    latitude: float
    longitude: float
    place_id: UUID | None = None
    location_note: str = ""
    precision: Literal["exact", "street", "parish", "town", "inferred"] = "inferred"
    date_text: str = ""
    year_from: int | None = None
    year_to: int | None = None
    date_role: Literal["event", "made"] = "event"
    file_id: UUID | None = None
    interview_id: UUID | None = None
    lines: list[int] = []


class ItemPatch(Schema):
    title: str | None = None
    text: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_note: str | None = None
    precision: Literal["exact", "street", "parish", "town", "inferred"] | None = None
    date_text: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    date_role: Literal["event", "made"] | None = None


def _check_point(lat: float | None, lng: float | None) -> None:
    if lat is not None and not -90 <= lat <= 90:
        raise HttpError(422, "That location is off the map.")
    if lng is not None and not -180 <= lng <= 180:
        raise HttpError(422, "That location is off the map.")


def _precision(year_from: int | None, year_to: int | None) -> str:
    if year_from is None and year_to is None:
        return DatePrecision.UNKNOWN
    if year_from is not None and year_to is not None and year_from != year_to:
        return DatePrecision.RANGE
    return DatePrecision.YEAR


@router.get("/projects/{project_id}/map-items")
def list_items(request: HttpRequest, project_id: UUID) -> list[dict[str, Any]]:
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    qs = MapItem.objects.filter(project=project).select_related("project", "place__parent")
    return [item_feature(i).to_dict() for i in qs]


@router.post("/projects/{project_id}/map-items", response={201: dict})
def add_item(request: HttpRequest, project_id: UUID, payload: ItemIn):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    title = payload.title.strip()[:200]
    if not title:
        raise HttpError(422, "Give it a short title.")
    _check_point(payload.latitude, payload.longitude)
    _year(payload.year_from), _year(payload.year_to)

    file = interview = None
    if payload.kind in (ItemKind.PHOTO, ItemKind.DOCUMENT):
        if not payload.file_id:
            raise HttpError(422, "Choose a file from this project's Archive.")
        file = FileAsset.objects.filter(project=project, pk=payload.file_id).first()
        if file is None:
            raise HttpError(422, "That file isn't in this project.")
        if payload.kind == ItemKind.PHOTO and file.kind != FileKind.IMAGE:
            raise HttpError(422, "That file isn't a photo.")
    if payload.kind == ItemKind.INTERVIEW:
        interview = InterviewSession.objects.filter(
            chat__project=project, pk=payload.interview_id
        ).first()
        if interview is None:
            raise HttpError(422, "That interview isn't in this project.")
        known = set(interview.segments.values_list("line", flat=True))
        if any(n not in known for n in payload.lines):
            raise HttpError(422, "Those transcript lines don't exist.")
    if payload.kind == ItemKind.MEMORY and not payload.text.strip():
        raise HttpError(422, "Write the memory down first.")
    place = Place.objects.filter(pk=payload.place_id).first() if payload.place_id else None

    item = MapItem.objects.create(
        project=project,
        kind=payload.kind,
        title=title,
        text=payload.text.strip()[:5000],
        file=file,
        interview=interview,
        lines=payload.lines if interview else [],
        place=place,
        latitude=payload.latitude,
        longitude=payload.longitude,
        geocode_precision=payload.precision,
        location_note=payload.location_note.strip()[:300],
        date_text=payload.date_text.strip()[:100],
        year_from=payload.year_from,
        year_to=payload.year_to,
        date_precision=_precision(payload.year_from, payload.year_to),
        date_role=payload.date_role,
        created_by=request.user,
    )
    audit(request.user, "map_item.create", item, project=str(project.id), kind=item.kind)
    return Status(201, item_feature(item).to_dict())


def _editable_item(user, item_id: UUID) -> MapItem:
    return get_object_or_404(
        MapItem.objects.select_related("project", "place__parent"),
        pk=item_id,
        project__in=editable_projects(user),
    )


@router.patch("/map-items/{item_id}")
def update_item(request: HttpRequest, item_id: UUID, payload: ItemPatch) -> dict[str, Any]:
    item = _editable_item(request.user, item_id)
    data = payload.dict(exclude_unset=True)
    _check_point(data.get("latitude"), data.get("longitude"))
    _year(data.get("year_from")), _year(data.get("year_to"))
    if "title" in data:
        if not (data["title"] or "").strip():
            raise HttpError(422, "Give it a short title.")
        item.title = data["title"].strip()[:200]
    for name in ("text", "location_note", "date_text"):
        if data.get(name) is not None:
            setattr(item, name, data[name].strip())
    for name in ("latitude", "longitude", "date_role"):
        if data.get(name) is not None:
            setattr(item, name, data[name])
    if data.get("precision"):
        item.geocode_precision = data["precision"]
    if "year_from" in data or "year_to" in data:
        item.year_from = data.get("year_from", item.year_from)
        item.year_to = data.get("year_to", item.year_to)
        item.date_precision = _precision(item.year_from, item.year_to)
    item.save()
    audit(request.user, "map_item.update", item, fields=sorted(data))
    return item_feature(item).to_dict()


@router.delete("/map-items/{item_id}", response={204: None})
def delete_item(request: HttpRequest, item_id: UUID):
    item = _editable_item(request.user, item_id)
    audit(request.user, "map_item.delete", item, project=str(item.project_id))
    item.delete()
    return Status(204, None)
