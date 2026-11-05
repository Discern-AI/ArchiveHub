"""Connector implementations and the registry."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import truststore

from history.models import SourceRecord
from history.queries import search_records

from .base import (
    AccessDenied,
    BadQuery,
    ConnectorRecord,
    NotFound,
    Page,
    RateLimited,
    SourceConnector,
    Unavailable,
    decode_cursor,
    encode_cursor,
)
from .models import Dataset, DatasetRow

USER_AGENT = "ArchiveHubBot/0.1 (https://github.com/Discern-AI/ArchiveHub) python-urllib"

# Verify certificates with the operating system's own trust store and chain building
# (full verification; avoids OpenSSL picking stale chains from the Windows store).
_TLS = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _size(page_size: int, maximum: int) -> int:
    return max(1, min(int(page_size or 25), maximum))


# --- Checked reference records (hosted, our own wording) --------------------------


class ReferenceConnector(SourceConnector):
    key = "checked-reference"
    name = "ArchiveHub checked records"
    source_key = "pub-wiki"
    access_type = "hosted"
    storage = "reference_only"
    description = "Hand-checked facts about Cheap Street and central Newbury, with links."

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        size = _size(page_size, self.max_page_size)
        offset = int(decode_cursor(cursor).get("offset", 0))
        if query.strip():
            matches = search_records(query, limit=500)
        else:
            matches = list(SourceRecord.objects.select_related("source", "place").order_by("title"))
        chunk = matches[offset : offset + size]
        more = offset + size < len(matches)
        return Page(
            records=[self._record(r) for r in chunk],
            next_cursor=encode_cursor({"offset": offset + size}) if more else None,
            searched=f"ArchiveHub's checked records for “{query}”" if query else "",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        record = (
            SourceRecord.objects.select_related("source", "place").filter(key=record_id).first()
        )
        if record is None:
            raise NotFound(record_id)
        return self._record(record)

    def _record(self, r: SourceRecord) -> ConnectorRecord:
        return ConnectorRecord(
            connector=self.key,
            id=r.key,
            title=r.title,
            description=r.summary,
            record_type=r.record_type,
            url=r.url,
            date_text=r.date_display,
            fields={"source": r.source.name, "checked_on": str(r.checked_on or ""), **r.fields},
            rights="Our own summary; see the linked page for the original",
            attribution=r.source.name,
        )


# --- Old map names, from the GB1900 raw data dump (hosted, CC0) ---------------------


class OldMapNamesConnector(SourceConnector):
    """Names from the OS six-inch maps of c.1900. Named without "GB1900", as the licence
    requires for derived works; the original is cited."""

    key = "old-map-names"
    dataset_key = "old-map-names"
    name = "Old map names (OS six-inch, c.1900)"
    source_key = "gb1900"
    access_type = "hosted"
    capabilities = frozenset({"search", "browse", "record_detail", "geo"})
    storage = "full_copy"
    licence = "CC0 1.0"
    attribution = (
        "From the GB1900 final raw gazetteer data dump, made available by the GB1900 Project"
    )
    description = (
        "Every label volunteers transcribed from the six-inch Ordnance Survey maps of about "
        "1900: place names, buildings, and abbreviations such as P.H. (public house)."
    )

    def dataset(self) -> Dataset:
        ds = Dataset.objects.filter(key=self.dataset_key).first()
        if ds is None:
            raise Unavailable("Dataset not imported yet. Run import_old_map_names.")
        return ds

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        size = _size(page_size, self.max_page_size)
        ds = self.dataset()
        rows = DatasetRow.objects.filter(dataset=ds)
        q = query.strip().lower()
        if q:
            rows = rows.filter(title_lower__contains=q)
        after = decode_cursor(cursor)
        if after:
            if not {"t", "i"} <= after.keys():
                raise BadQuery("Invalid cursor")
            rows = rows.filter(title_lower__gt=after["t"]) | rows.filter(
                title_lower=after["t"], id__gt=after["i"]
            )
        chunk = list(rows.order_by("title_lower", "id")[: size + 1])
        more = len(chunk) > size
        chunk = chunk[:size]
        next_cursor = (
            encode_cursor({"t": chunk[-1].title_lower, "i": chunk[-1].id}) if more else None
        )
        return Page(
            records=[self._record(r) for r in chunk],
            next_cursor=next_cursor,
            searched=f"{self.name} for “{query}” ({ds.import_scope})",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        row = DatasetRow.objects.filter(dataset=self.dataset(), external_id=record_id).first()
        if row is None:
            raise NotFound(record_id)
        return self._record(row)

    def _record(self, row: DatasetRow) -> ConnectorRecord:
        variants = row.fields.get("variants", [])
        return ConnectorRecord(
            connector=self.key,
            id=row.external_id,
            title=row.title,
            description="Label on the OS six-inch map, c.1900"
            + (f". Other readings: {', '.join(variants)}" if variants else ""),
            record_type="map label",
            date_text="c.1900",
            latitude=row.latitude,
            longitude=row.longitude,
            fields=row.fields,
            rights="CC0 1.0",
            attribution=self.attribution,
        )


# --- Wikidata (live API, CC0) ------------------------------------------------------


def http_get_json(url: str, params: dict[str, Any], timeout: float = 10.0) -> Any:
    """GET JSON with a descriptive User-Agent, mapping failures onto connector errors."""
    full = f"{url}?{urllib.parse.urlencode(params)}"
    if not url.startswith("https://"):
        raise BadQuery("Only https sources are allowed")
    request = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_TLS) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RateLimited(str(exc)) from exc
        if exc.code in (401, 403):
            raise AccessDenied(str(exc)) from exc
        if exc.code == 404:
            raise NotFound(str(exc)) from exc
        raise Unavailable(str(exc)) from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise Unavailable(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise Unavailable("Unreadable response") from exc


class WikidataConnector(SourceConnector):
    key = "wikidata"
    name = "Wikidata"
    source_key = "wikidata"
    access_type = "live_api"
    storage = "full_copy"  # CC0, confirmed 2026-11-05
    licence = "CC0 1.0"
    attribution = "Wikidata"
    description = "Live search of Wikidata's people, places and organisations. Context, not proof."
    api = "https://www.wikidata.org/w/api.php"
    max_page_size = 50

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        if not query.strip():
            raise BadQuery("Wikidata needs a search term")
        size = _size(page_size, self.max_page_size)
        offset = int(decode_cursor(cursor).get("offset", 0))
        data = http_get_json(
            self.api,
            {
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "uselang": "en",
                "type": "item",
                "limit": size,
                "continue": offset,
                "format": "json",
            },
        )
        if "error" in data:
            raise BadQuery(data["error"].get("info", "Search failed"))
        records = [
            ConnectorRecord(
                connector=self.key,
                id=item["id"],
                title=item.get("label") or item["id"],
                description=item.get("description", ""),
                record_type="Wikidata item",
                url=f"https://www.wikidata.org/wiki/{item['id']}",
                rights="CC0 1.0",
                attribution="Wikidata",
            )
            for item in data.get("search", [])
        ]
        more = data.get("search-continue")
        return Page(
            records=records,
            next_cursor=encode_cursor({"offset": more}) if more else None,
            searched=f"Wikidata (live) for “{query}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not (record_id[:1] == "Q" and record_id[1:].isdigit()):
            raise NotFound(record_id)
        data = http_get_json(
            self.api,
            {
                "action": "wbgetentities",
                "ids": record_id,
                "props": "labels|descriptions|claims|sitelinks/urls",
                "languages": "en",
                "sitefilter": "enwiki",
                "format": "json",
            },
        )
        entity = data.get("entities", {}).get(record_id)
        if not entity or "missing" in entity:
            raise NotFound(record_id)
        claims = entity.get("claims", {})
        coords = _claim_value(claims, "P625") or {}
        fields = {
            "instance_of": [
                v.get("id") for v in _claim_values(claims, "P31") if isinstance(v, dict)
            ],
            "inception": _time(_claim_value(claims, "P571")),
            "dissolved_or_demolished": _time(_claim_value(claims, "P576")),
            "wikipedia": entity.get("sitelinks", {}).get("enwiki", {}).get("url"),
        }
        return ConnectorRecord(
            connector=self.key,
            id=record_id,
            title=entity.get("labels", {}).get("en", {}).get("value", record_id),
            description=entity.get("descriptions", {}).get("en", {}).get("value", ""),
            record_type="Wikidata item",
            url=f"https://www.wikidata.org/wiki/{record_id}",
            latitude=coords.get("latitude"),
            longitude=coords.get("longitude"),
            fields={k: v for k, v in fields.items() if v},
            rights="CC0 1.0",
            attribution="Wikidata",
        )


def _claim_values(claims: dict, prop: str) -> list[Any]:
    out = []
    for claim in claims.get(prop, []):
        snak = claim.get("mainsnak", {})
        if snak.get("snaktype") == "value":
            out.append(snak.get("datavalue", {}).get("value"))
    return out


def _claim_value(claims: dict, prop: str) -> Any:
    values = _claim_values(claims, prop)
    return values[0] if values else None


def _time(value: Any) -> str | None:
    if isinstance(value, dict) and value.get("time"):
        t = value["time"].lstrip("+")
        precision = value.get("precision", 11)
        return t[:4] if precision <= 9 else t[:10]
    return None


# --- Registry ----------------------------------------------------------------------

CONNECTORS: dict[str, SourceConnector] = {
    c.key: c for c in (ReferenceConnector(), OldMapNamesConnector(), WikidataConnector())
}


def get_connector(key: str) -> SourceConnector:
    try:
        return CONNECTORS[key]
    except KeyError:
        raise NotFound(f"No connector {key!r}") from None
