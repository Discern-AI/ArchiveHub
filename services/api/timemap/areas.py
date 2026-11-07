"""Protected areas on the time map, live from Historic England's open services (OGL).

Conservation areas, scheduled monuments, registered parks and gardens, and registered
battlefields, as outlines. Like listed buildings, they're shown for every year: the date
given is when the area was designated, not when it was made.
"""

from __future__ import annotations

from typing import Any

from django.core.cache import cache

from connectors.base import ConnectorError
from connectors.sources import http_get_json

from .queries import BBox

ARCGIS = "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services"
NHLE = f"{ARCGIS}/National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer"
LAYERS = [
    # kind, label, query URL, name field, date field, link field
    (
        "conservation_area",
        "Conservation area",
        f"{ARCGIS}/Conservation_Areas/FeatureServer/0/query",
        "NAME",
        "DATE_OF_DE",
        None,
    ),
    (
        "scheduled_monument",
        "Scheduled monument",
        f"{NHLE}/6/query",
        "Name",
        "SchedDate",
        "hyperlink",
    ),
    ("park_garden", "Registered park or garden", f"{NHLE}/7/query", "Name", "RegDate", "hyperlink"),
    ("battlefield", "Registered battlefield", f"{NHLE}/8/query", "Name", "RegDate", "hyperlink"),
]
MAX_SPAN = 0.3  # degrees: about a town and its surroundings
CACHE_SECONDS = 24 * 3600
ATTRIBUTION = (
    "© Historic England and local planning authorities. Contains Ordnance Survey data © Crown "
    "copyright and database right. Open Government Licence."
)


def _year(value: Any) -> str:
    if isinstance(value, int | float):
        from datetime import UTC, datetime, timedelta

        return str((datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=value)).year)
    if isinstance(value, str) and value[-4:].isdigit():
        return value[-4:]
    return ""


def protected_areas(bbox: BBox) -> dict[str, Any]:
    if (bbox.east - bbox.west) > MAX_SPAN or (bbox.north - bbox.south) > MAX_SPAN:
        return {
            "type": "FeatureCollection",
            "features": [],
            "notes": ["Zoom in to see protected areas."],
        }
    key = "areas:" + ",".join(f"{v:.2f}" for v in (bbox.west, bbox.south, bbox.east, bbox.north))
    cached = cache.get(key)
    if cached is not None:
        return cached
    # Ask for a slightly larger area, rounded, so nearby views share the cache.
    w, s, e, n = (
        round(v, 2)
        for v in (bbox.west - 0.01, bbox.south - 0.01, bbox.east + 0.01, bbox.north + 0.01)
    )
    features, notes = [], []
    for kind, label, url, name_field, date_field, link_field in LAYERS:
        try:
            data = http_get_json(
                url,
                {
                    "where": "1=1",
                    "geometry": f"{w},{s},{e},{n}",
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": 4326,
                    "outSR": 4326,
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "*",
                    "maxAllowableOffset": 0.00005,
                    "resultRecordCount": 200,
                    "f": "geojson",
                },
                timeout=15.0,
            )
        except ConnectorError:
            notes.append(f"{label}s couldn't be loaded from Historic England just now.")
            continue
        for i, f in enumerate(data.get("features", []) or []):
            props = f.get("properties") or {}
            if not f.get("geometry"):
                continue
            year = _year(props.get(date_field))
            features.append(
                {
                    "type": "Feature",
                    "id": f"{kind}:{props.get('ListEntry') or props.get('UID') or i}",
                    "geometry": f["geometry"],
                    "properties": {
                        "kind": kind,
                        "label": label,
                        "name": str(props.get(name_field) or label),
                        "designated": year,
                        "url": (props.get(link_field) if link_field else "") or "",
                        "authority": props.get("LPA") or "",
                    },
                }
            )
    result = {"type": "FeatureCollection", "features": features, "notes": notes}
    if not notes:
        cache.set(key, result, CACHE_SECONDS)
    return result
