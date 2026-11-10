"""Listed buildings across the UK, from each nation's own list (all OGL).

England: Historic England's National Heritage List. Scotland: Historic Environment
Scotland. Wales: Cadw (via DataMapWales). These three are asked live. Northern Ireland:
the Department for Communities' list from Open Data NI, imported monthly (there's no
open live service), with the date range each was built rather than a listing date.
Each building keeps its own list's grade or category, date, link and credit. A listing
date is not a build date.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

from connectors.base import ConnectorError
from connectors.sources import http_get_json

from .queries import BBox

ENGLAND = (
    "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/"
    "National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer/0/query"
)
SCOTLAND = "https://inspire.hes.scot/arcgis/rest/services/HES/Listed_Buildings/MapServer/0/query"
WALES = "https://datamap.gov.wales/geoserver/ows"

CREDITS = {
    "england": "© Historic England. Contains Ordnance Survey data © Crown copyright and "
    "database right. Open Government Licence.",
    "scotland": "Contains Historic Environment Scotland and Ordnance Survey data © Historic "
    "Environment Scotland – Scottish Charity No. SC045925; © Crown copyright and database "
    "right. Open Government Licence.",
    "wales": "Designated Historic Asset GIS Data, The Welsh Historic Environment Service "
    "(Cadw). Open Government Licence.",
    "northern_ireland": "Listed Buildings Northern Ireland, Department for Communities "
    "Historic Environment Division, via Open Data NI. Open Government Licence.",
}
SOURCES = {
    "england": "National Heritage List for England (Historic England)",
    "scotland": "Historic Environment Scotland",
    "wales": "Cadw (Welsh Historic Environment Service)",
    "northern_ireland": "Department for Communities, Historic Environment Division",
}
NI_VIEWER = "https://www.communities-ni.gov.uk/services/historic-environment-map-viewer"
# Roughly Northern Ireland, to say when its list hasn't been imported.
NI_BOX = BBox(-8.25, 54.0, -5.4, 55.35)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _year(value: Any) -> str:
    if isinstance(value, int | float):
        return str((_EPOCH + timedelta(milliseconds=value)).year)
    if isinstance(value, str) and value[:4].isdigit():
        return value[:4]
    return ""


def _envelope(b: BBox) -> dict[str, Any]:
    return {
        "geometry": f"{b.west},{b.south},{b.east},{b.north}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "f": "json",
    }


def _england(b: BBox, limit: int) -> tuple[list[dict], bool]:
    data = http_get_json(
        ENGLAND,
        {
            "where": "1=1",
            "outFields": "ListEntry,Name,Grade,ListDate,hyperlink",
            "resultRecordCount": limit,
            **_envelope(b),
        },
        timeout=15.0,
    )
    out = []
    for f in data.get("features", []) or []:
        a, pts = f.get("attributes") or {}, (f.get("geometry") or {}).get("points") or []
        if not pts:
            continue
        out.append(
            {
                "nation": "england",
                "id": f"en:{a.get('ListEntry')}",
                "title": a.get("Name") or "",
                "grade": f"Grade {a['Grade']}" if a.get("Grade") else "",
                "listed": _year(a.get("ListDate")),
                "url": a.get("hyperlink") or "",
                "latitude": pts[0][1],
                "longitude": pts[0][0],
            }
        )
    return out, bool(data.get("exceededTransferLimit"))


def _scotland(b: BBox, limit: int) -> tuple[list[dict], bool]:
    # This service doesn't page, so ask and cut; one building can have several points.
    data = http_get_json(
        SCOTLAND,
        {"where": "1=1", "outFields": "DES_REF,DES_TITLE,CATEGORY,DESIGNATED,LINK", **_envelope(b)},
        timeout=15.0,
    )
    seen, out = set(), []
    for f in data.get("features", []) or []:
        a, g = f.get("attributes") or {}, f.get("geometry") or {}
        ref = a.get("DES_REF")
        if not ref or ref in seen or g.get("x") is None:
            continue
        seen.add(ref)
        out.append(
            {
                "nation": "scotland",
                "id": f"sc:{ref}",
                "title": a.get("DES_TITLE") or ref,
                "grade": f"Category {a['CATEGORY']}" if a.get("CATEGORY") else "",
                "listed": _year(a.get("DESIGNATED")),
                "url": a.get("LINK")
                or f"https://portal.historicenvironment.scot/designation/{ref}",
                "latitude": g["y"],
                "longitude": g["x"],
            }
        )
    return out[:limit], len(out) > limit


def _wales(b: BBox, limit: int) -> tuple[list[dict], bool]:
    data = http_get_json(
        WALES,
        {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": "inspire-wg:Cadw_ListedBuildings",
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
            # CRS:84 is longitude first, like everything else here.
            "bbox": f"{b.west},{b.south},{b.east},{b.north},CRS:84",
            "count": limit + 1,
        },
        timeout=15.0,
    )
    out = []
    for f in data.get("features", []) or []:
        p, coords = f.get("properties") or {}, (f.get("geometry") or {}).get("coordinates") or []
        if not coords:
            continue
        lng, lat = coords[0] if isinstance(coords[0], list) else coords
        out.append(
            {
                "nation": "wales",
                "id": f"cy:{p.get('RecordNumber')}",
                "title": p.get("Name") or "",
                "grade": f"Grade {p['Grade']}" if p.get("Grade") else "",
                "listed": _year(p.get("DesignationDate")),
                "url": p.get("Report") or "",
                "latitude": lat,
                "longitude": lng,
            }
        )
    return out[:limit], len(out) > limit


def _northern_ireland(b: BBox, limit: int) -> tuple[list[dict], bool]:
    from connectors.models import DatasetRow

    rows = list(
        DatasetRow.objects.filter(dataset__key="ni-listed-buildings")
        .filter(b.q())
        .order_by("external_id")[: limit + 1]
    )
    out = [
        {
            "nation": "northern_ireland",
            "id": f"ni:{r.external_id}",
            "title": r.title,
            "grade": f"Grade {r.fields.get('grade')}" if r.fields.get("grade") else "",
            "listed": "",
            "built": r.fields.get("built", ""),
            "ref": r.external_id,
            "address": r.fields.get("address", ""),
            "url": NI_VIEWER,
            "latitude": r.latitude,
            "longitude": r.longitude,
        }
        for r in rows
    ]
    return out[:limit], len(out) > limit


def _overlaps(a: BBox, b: BBox) -> bool:
    return a.west < b.east and b.west < a.east and a.south < b.north and b.south < a.north


FETCHERS = {"england": _england, "scotland": _scotland, "wales": _wales}


def listed_in(b: BBox, limit: int = 300) -> tuple[list[dict], bool, list[str]]:
    """(buildings, more_than_limit, notes) from every nation's list, asked at once."""
    buildings, more, notes = [], False, []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {nation: pool.submit(fetch, b, limit) for nation, fetch in FETCHERS.items()}
    for nation, future in futures.items():
        try:
            found, over = future.result()
        except ConnectorError:
            notes.append(f"Listed buildings from {SOURCES[nation]} couldn't be loaded just now.")
            continue
        buildings += found
        more = more or over
    # Northern Ireland is our own copy, so it's read here rather than in the pool.
    if _overlaps(b, NI_BOX):
        from connectors.models import Dataset

        if Dataset.objects.filter(key="ni-listed-buildings").exists():
            found, over = _northern_ireland(b, limit)
            buildings += found
            more = more or over
        else:
            notes.append("Northern Ireland's listed buildings haven't been loaded here yet.")
    return buildings, more, notes
