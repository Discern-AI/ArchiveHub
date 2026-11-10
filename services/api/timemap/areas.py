"""Protected areas on the time map, live from each nation's own open services (all OGL).

Conservation areas, scheduled monuments, registered parks and gardens, and battlefields,
as outlines. England: Historic England. Scotland: Historic Environment Scotland (its
conservation areas are compiled from the local authorities). Wales: Cadw and the Welsh
Government, via DataMapWales (Wales has no battlefields layer). Northern Ireland isn't
connected yet. Like listed buildings, they're shown for every year: the date given is
when the area was designated, not when it was made.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from django.core.cache import cache

from connectors.base import ConnectorError
from connectors.sources import http_get_json

from .queries import BBox

ARCGIS = "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services"
NHLE = f"{ARCGIS}/National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer"
HES = "https://inspire.hes.scot/arcgis/rest/services/HES"
WALES_WFS = "https://datamap.gov.wales/geoserver/ows"


@dataclass(frozen=True)
class Layer:
    nation: str
    kind: str
    label: str
    url: str  # an ArcGIS query URL, or a WFS type name for Wales
    name: str
    date: str
    link: str = ""
    ref: str = ""
    authority: str = ""
    pages: bool = True  # HES's MapServers refuse resultRecordCount


LAYERS = [
    Layer("england", "conservation_area", "Conservation area",
          f"{ARCGIS}/Conservation_Areas/FeatureServer/0/query", "NAME", "DATE_OF_DE",
          ref="UID", authority="LPA"),
    Layer("england", "scheduled_monument", "Scheduled monument", f"{NHLE}/6/query", "Name",
          "SchedDate", "hyperlink", "ListEntry"),
    Layer("england", "park_garden", "Registered park or garden", f"{NHLE}/7/query", "Name",
          "RegDate", "hyperlink", "ListEntry"),
    Layer("england", "battlefield", "Registered battlefield", f"{NHLE}/8/query", "Name",
          "RegDate", "hyperlink", "ListEntry"),
    Layer("scotland", "conservation_area", "Conservation area",
          f"{HES}/Conservation_Areas/MapServer/0/query", "DES_TITLE", "DESIGNATED", "LINK",
          "DES_REF", "LOCAL_AUTH", pages=False),
    Layer("scotland", "scheduled_monument", "Scheduled monument",
          f"{HES}/Scheduled_Monuments/MapServer/0/query", "DES_TITLE", "DESIGNATED", "LINK",
          "DES_REF", "LOCAL_AUTH", pages=False),
    Layer("scotland", "park_garden", "Garden and designed landscape",
          f"{HES}/Gardens_and_Designed_Landscapes/MapServer/0/query", "DES_TITLE",
          "DESIGNATED", "LINK", "DES_REF", "LOCAL_AUTH", pages=False),
    Layer("scotland", "battlefield", "Inventory battlefield",
          f"{HES}/Battlefields_Inventory_Boundary/MapServer/0/query", "DES_TITLE",
          "DESIGNATED", "LINK", "DES_REF", "LOCAL_AUTH", pages=False),
    Layer("wales", "conservation_area", "Conservation area", "geonode:conservation_areas_wales",
          "sitename", "designation_date", authority="localplann"),
    Layer("wales", "scheduled_monument", "Scheduled monument", "inspire-wg:Cadw_SAM", "Name",
          "DesignationDate", "Report", "SAMNumber", "UnitaryAuthority"),
    Layer("wales", "park_garden", "Registered historic park or garden",
          "geonode:cadw_rhpg_registeredareas", "site_name_en", "designation_date", "report_en",
          "reference_number", "la_en"),
]  # fmt: skip

# Roughly each nation (a few boxes each, so they don't cover Northern Ireland), so a view
# only asks the services it could need.
NATION_BOXES = {
    "england": [BBox(-6.5, 49.8, 1.9, 51.6), BBox(-3.8, 51.6, 1.9, 55.9)],
    "scotland": [BBox(-8.7, 55.3, -0.7, 60.9), BBox(-5.2, 54.6, -1.7, 55.3)],
    "wales": [BBox(-5.4, 51.3, -2.6, 53.5)],
}
NI_BOX = BBox(-8.25, 54.0, -5.4, 55.35)
HOLDERS = {
    "england": "Historic England",
    "scotland": "Historic Environment Scotland",
    "wales": "DataMapWales",
}
CREDITS = {
    "england": "© Historic England and local planning authorities. Contains Ordnance Survey "
    "data © Crown copyright and database right. Open Government Licence.",
    "scotland": "Contains Historic Environment Scotland and Ordnance Survey data © Historic "
    "Environment Scotland – Scottish Charity No. SC045925; © Crown copyright and database "
    "right. Conservation areas from the local authorities. Open Government Licence.",
    "wales": "Designated Historic Asset GIS Data, The Welsh Historic Environment Service "
    "(Cadw); conservation areas from the Welsh Government and local planning authorities "
    "(DataMapWales). Open Government Licence.",
}
ATTRIBUTION = CREDITS["england"]  # kept for callers that want a default
MAX_SPAN = 0.3  # degrees: about a town and its surroundings
CACHE_SECONDS = 24 * 3600
LIMIT = 200
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _year(value: Any) -> str:
    if isinstance(value, int | float):
        return str((_EPOCH + timedelta(milliseconds=value)).year)
    if isinstance(value, str):
        value = value.strip()
        if value[:4].isdigit() and value[4:5] == "-":  # 1984-06-01, ISO dates
            return value[:4]
        if value[-4:].isdigit():  # 03/1971
            return value[-4:]
    return ""


def _name(value: Any) -> str:
    """Names as written, except all-capitals ones ("CULLODEN MUIR"), which are softened."""
    name = " ".join(str(value or "").split())
    return name.title() if name.isupper() else name


def _overlaps(a: BBox, b: BBox) -> bool:
    return a.west < b.east and b.west < a.east and a.south < b.north and b.south < a.north


def _fetch(layer: Layer, w: float, s: float, e: float, n: float) -> list[dict]:
    if layer.nation == "wales":
        data = http_get_json(
            WALES_WFS,
            {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": layer.url,
                "outputFormat": "application/json",
                "srsName": "EPSG:4326",
                # CRS:84 is longitude first, like everything else here.
                "bbox": f"{w},{s},{e},{n},CRS:84",
                "count": LIMIT,
            },
            timeout=15.0,
        )
    else:
        params: dict[str, Any] = {
            "where": "1=1",
            "geometry": f"{w},{s},{e},{n}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "outSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "maxAllowableOffset": 0.00005,
            "f": "geojson",
        }
        if layer.pages:
            params["resultRecordCount"] = LIMIT
        data = http_get_json(layer.url, params, timeout=15.0)
    return (data.get("features", []) or [])[:LIMIT]


def protected_areas(bbox: BBox) -> dict[str, Any]:
    if (bbox.east - bbox.west) > MAX_SPAN or (bbox.north - bbox.south) > MAX_SPAN:
        return {
            "type": "FeatureCollection",
            "features": [],
            "notes": ["Zoom in to see protected areas."],
            "attribution": ATTRIBUTION,
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
    asked = BBox(w, s, e, n)
    nations = [k for k, boxes in NATION_BOXES.items() if any(_overlaps(asked, b) for b in boxes)]
    layers = [layer for layer in LAYERS if layer.nation in nations]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [(layer, pool.submit(_fetch, layer, w, s, e, n)) for layer in layers]
    features, notes = [], []
    for layer, future in futures:
        try:
            found = future.result()
        except ConnectorError:
            notes.append(
                f"{layer.label}s couldn't be loaded from {HOLDERS[layer.nation]} just now."
            )
            continue
        for i, f in enumerate(found):
            props = f.get("properties") or {}
            if not f.get("geometry"):
                continue
            ref = props.get(layer.ref) if layer.ref else None
            features.append(
                {
                    "type": "Feature",
                    "id": f"{layer.nation}:{layer.kind}:{ref or i}",
                    "geometry": f["geometry"],
                    "properties": {
                        "kind": layer.kind,
                        "label": layer.label,
                        "name": _name(props.get(layer.name)) or layer.label,
                        "designated": _year(props.get(layer.date)),
                        "url": (props.get(layer.link) if layer.link else "") or "",
                        "authority": str(props.get(layer.authority) or "").strip()
                        if layer.authority
                        else "",
                        "nation": layer.nation,
                    },
                }
            )
    coverage = []
    if _overlaps(asked, NI_BOX):
        coverage.append("Northern Ireland's protected areas aren't connected yet.")
    elif not nations:
        coverage.append("Protected areas aren't connected for this part of the map yet.")
    result = {
        "type": "FeatureCollection",
        "features": features,
        "notes": notes + coverage,
        "attribution": " ".join(CREDITS[k] for k in nations) or ATTRIBUTION,
    }
    if not notes:
        cache.set(key, result, CACHE_SECONDS)
    return result
