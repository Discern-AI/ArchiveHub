"""Live connectors that need a key or registered access (ADR-034).

Each one reads its key from settings. Without it, the source is listed as "not set up
on this server yet" and every call says so plainly: never an empty result that could be
mistaken for "nothing exists". Results are fetched live; what may be kept follows each
source's terms (`storage`). Error messages never contain the request URL, so keys can't
leak.
"""

from __future__ import annotations

import math
import re
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from django.conf import settings

from .base import (
    AccessDenied,
    BadQuery,
    ConnectorError,
    ConnectorRecord,
    NotFound,
    Page,
    RateLimited,
    SourceConnector,
    decode_cursor,
    encode_cursor,
)


def _sources():
    """The shared HTTP helper lives in sources.py, which imports this module's registry."""
    from . import sources

    return sources


def _size(page_size: int, maximum: int) -> int:
    return _sources()._size(page_size, maximum)


class NotConfigured(ConnectorError):
    kind = "not_configured"
    user_message = "This source isn't set up on this server yet."


def _first(value: Any) -> str:
    """Providers often wrap single values in lists."""
    if isinstance(value, list):
        value = next((v for v in value if v), "")
    if isinstance(value, dict):
        value = value.get("def") or value.get("en") or next(iter(value.values()), "")
        return _first(value)
    return str(value).strip() if value is not None else ""


def _clip(text: str, n: int = 600) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _float(value: Any) -> float | None:
    try:
        f = float(_first(value))
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _page_number(cursor: str | None) -> int:
    page = decode_cursor(cursor).get("page", 1)
    if not isinstance(page, int) or page < 1:
        raise BadQuery("Invalid cursor")
    return page


class LiveConnector(SourceConnector):
    """A live API that needs a key (or registered access) from settings."""

    access_type = "live_api"
    setting: ClassVar[str] = ""  # settings attribute holding the key
    setup_note: ClassVar[str] = ""  # what the owner needs to do, shown when not set up
    min_interval: ClassVar[float] = 0.0  # seconds between requests (provider guidance)
    _lock: ClassVar[threading.Lock]
    _last: ClassVar[float]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._lock = threading.Lock()
        cls._last = 0.0

    # Key handling --------------------------------------------------------------

    @property
    def key_value(self) -> str:
        value = getattr(settings, self.setting, "")
        return value if isinstance(value, str) else ""

    def configured(self) -> bool:
        return bool(self.key_value)

    def require_key(self) -> str:
        if not self.configured():
            raise NotConfigured(self.setup_note)
        return self.key_value

    def describe(self) -> dict[str, Any]:
        info = super().describe()
        info["configured"] = self.configured()
        info["setup_note"] = "" if self.configured() else self.setup_note
        return info

    # Requests -----------------------------------------------------------------

    def get(self, url: str, params: dict[str, Any], headers: dict[str, str] | None = None):
        self.require_key()
        if self.min_interval:
            with self._lock:
                wait = type(self)._last + self.min_interval - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                type(self)._last = time.monotonic()
        return _sources().http_get_json(url, params, timeout=12.0, headers=headers)

    def stored_label(self, record: ConnectorRecord) -> str:
        """What may be kept as this record's label (basket, citations)."""
        return record.title


def _require_query(query: str, name: str) -> str:
    q = query.strip()
    if not q:
        raise BadQuery(f"{name} needs a search term")
    return q


# --- Europeana (CC0 metadata; each object carries its own rights statement) ------------


class EuropeanaConnector(LiveConnector):
    key = "europeana"
    name = "Europeana"
    source_key = "europeana"
    setting = "EUROPEANA_API_KEY"
    setup_note = "Needs a Europeana project API key (free; personal keys are not for production)."
    storage = "metadata_only"
    licence = "Metadata CC0 1.0; each item has its own rights statement"
    attribution = "Europeana and the providing institution"
    description = (
        "Over 50 million items from European museums, libraries and archives: photos, "
        "documents, maps, sound and film."
    )
    api = "https://api.europeana.eu/record/v2/search.json"
    max_page_size = 50

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        mark = decode_cursor(cursor).get("mark", "*")
        if not isinstance(mark, str):
            raise BadQuery("Invalid cursor")
        data = self.get(
            self.api,
            {"wskey": self.require_key(), "query": q, "rows": size, "cursor": mark},
        )
        if data.get("success") is False:
            raise BadQuery(data.get("error", "Search failed"))
        records = [self._record(i) for i in data.get("items", [])]
        nxt = data.get("nextCursor")
        return Page(
            records=records,
            next_cursor=encode_cursor({"mark": nxt}) if nxt and records else None,
            searched=f"Europeana (live) for “{q}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not re.fullmatch(r'[^/\s"]+/[^\s"]+', record_id):
            raise NotFound(record_id)
        data = self.get(
            self.api,
            {"wskey": self.require_key(), "query": f'europeana_id:"/{record_id}"', "rows": 1},
        )
        items = data.get("items") or []
        if not items:
            raise NotFound(record_id)
        return self._record(items[0])

    def _record(self, i: dict[str, Any]) -> ConnectorRecord:
        rid = str(i.get("id", "")).lstrip("/")
        rights = _first(i.get("rights"))
        return ConnectorRecord(
            connector=self.key,
            id=rid,
            title=_first(i.get("title")) or rid,
            description=_clip(_first(i.get("dcDescription"))),
            record_type=_first(i.get("type")).lower(),
            url=_first(i.get("guid")) or f"https://www.europeana.eu/item/{rid}",
            date_text=_first(i.get("year")),
            latitude=_float(i.get("edmPlaceLatitude")),
            longitude=_float(i.get("edmPlaceLongitude")),
            fields={
                k: v
                for k, v in {
                    "held_by": _first(i.get("dataProvider")),
                    "country": _first(i.get("country")),
                    "original": _first(i.get("edmIsShownAt")),
                    "preview": _first(i.get("edmPreview")),
                    "rights_statement": rights,
                }.items()
                if v
            },
            rights=f"Item rights: {rights}" if rights else "See the item for its rights",
            attribution=_first(i.get("dataProvider")) or "Europeana",
        )


# --- Trove (National Library of Australia) ----------------------------------------------


class TroveConnector(LiveConnector):
    key = "trove"
    name = "Trove newspapers (National Library of Australia)"
    source_key = "trove"
    setting = "TROVE_API_KEY"
    setup_note = (
        "Needs a Trove API key. Commercial use needs the National Library of Australia's "
        "explicit permission (their commercial access level)."
    )
    storage = "reference_only"
    licence = "Trove API terms; commercial use only with NLA permission"
    attribution = "Trove, National Library of Australia"
    description = (
        "Australian newspapers 1803–1950s, digitised with searchable text. Useful for "
        "relatives who emigrated."
    )
    api = "https://api.trove.nla.gov.au/v3"
    max_page_size = 100

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        mark = decode_cursor(cursor).get("mark", "*")
        if not isinstance(mark, str):
            raise BadQuery("Invalid cursor")
        data = self.get(
            f"{self.api}/result",
            {"category": "newspaper", "q": q, "encoding": "json", "n": size, "s": mark},
            headers={"X-API-KEY": self.require_key()},
        )
        block = next((c for c in data.get("category", []) if c.get("code") == "newspaper"), {}).get(
            "records", {}
        )
        articles = block.get("article", []) or []
        nxt = block.get("nextStart")
        return Page(
            records=[self._record(a) for a in articles],
            next_cursor=encode_cursor({"mark": nxt}) if nxt and articles else None,
            searched=f"Trove newspapers (live) for “{q}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not record_id.isdigit():
            raise NotFound(record_id)
        data = self.get(
            f"{self.api}/newspaper/{record_id}",
            {"encoding": "json", "reclevel": "brief"},
            headers={"X-API-KEY": self.require_key()},
        )
        article = data.get("article", data)
        if not article.get("id"):
            raise NotFound(record_id)
        return self._record(article)

    def _record(self, a: dict[str, Any]) -> ConnectorRecord:
        rid = str(a.get("id", ""))
        paper = a.get("title")
        paper_name = paper.get("title", "") if isinstance(paper, dict) else _first(paper)
        snippet = re.sub(r"<[^>]+>", "", _first(a.get("snippet")))
        return ConnectorRecord(
            connector=self.key,
            id=rid,
            title=_first(a.get("heading")) or f"Article {rid}",
            description=_clip(snippet),
            record_type="newspaper article",
            url=_first(a.get("troveUrl")) or f"https://trove.nla.gov.au/newspaper/article/{rid}",
            date_text=_first(a.get("date")),
            fields={
                k: v
                for k, v in {"newspaper": paper_name, "page": _first(a.get("page"))}.items()
                if v
            },
            rights="See Trove for this article's rights",
            attribution="Trove, National Library of Australia",
        )


# --- DigitalNZ (incl. Papers Past) ----------------------------------------------------


class DigitalNZConnector(LiveConnector):
    key = "digitalnz"
    name = "DigitalNZ (incl. Papers Past newspapers)"
    source_key = "digitalnz"
    setting = "DIGITALNZ_API_KEY"
    setup_note = (
        "Needs a DigitalNZ API key: their terms allow commercial use of selected metadata "
        "only with a key."
    )
    storage = "reference_only"
    licence = "DigitalNZ Developer API terms (commercial); each item has its own rights"
    attribution = "The item's source, linked as DigitalNZ requires"
    description = (
        "New Zealand collections, including Papers Past newspapers and photos. Useful for "
        "relatives who emigrated."
    )
    api = "https://api.digitalnz.org/v3"
    max_page_size = 100

    def _headers(self) -> dict[str, str]:
        return {"Authentication-Token": self.require_key()}

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        page = _page_number(cursor)
        data = self.get(
            f"{self.api}/records.json",
            {"text": q, "page": page, "per_page": size},
            headers=self._headers(),
        )
        block = data.get("search", {})
        results = block.get("results", []) or []
        total = int(block.get("result_count") or 0)
        more = page * size < total and bool(results)
        return Page(
            records=[self._record(r) for r in results],
            next_cursor=encode_cursor({"page": page + 1}) if more else None,
            searched=f"DigitalNZ (live) for “{q}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not record_id.isdigit():
            raise NotFound(record_id)
        data = self.get(f"{self.api}/records/{record_id}.json", {}, headers=self._headers())
        record = data.get("record")
        if not record:
            raise NotFound(record_id)
        return self._record(record)

    def _record(self, r: dict[str, Any]) -> ConnectorRecord:
        rid = str(r.get("id", ""))
        partner = _first(r.get("display_content_partner")) or _first(r.get("content_partner"))
        return ConnectorRecord(
            connector=self.key,
            id=rid,
            title=_first(r.get("title")) or rid,
            description=_clip(_first(r.get("description"))),
            record_type=_first(r.get("category")).lower(),
            # DigitalNZ's terms: link each item to its source page via source_url.
            url=_first(r.get("source_url")) or _first(r.get("landing_url")),
            date_text=_first(r.get("display_date")),
            latitude=_float(r.get("lat")),
            longitude=_float(r.get("lng")),
            fields={
                k: v
                for k, v in {
                    "source": partner,
                    "page": _first(r.get("landing_url")),
                    "usage": ", ".join(r.get("usage") or []),
                }.items()
                if v
            },
            rights=_first(r.get("rights")) or "See the source for rights",
            attribution=partner or "DigitalNZ",
        )


# --- DPLA (Digital Public Library of America) ----------------------------------------


class DPLAConnector(LiveConnector):
    key = "dpla"
    name = "Digital Public Library of America"
    source_key = "dpla"
    setting = "DPLA_API_KEY"
    setup_note = "Needs a DPLA API key (free, requested by email)."
    storage = "metadata_only"
    licence = "Metadata CC0; each item has its own rights"
    attribution = "DPLA and the contributing institution"
    description = "US libraries, archives and museums: photos, documents, books and maps."
    api = "https://api.dp.la/v2/items"
    max_page_size = 100

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        page = _page_number(cursor)
        data = self.get(
            self.api, {"q": q, "page_size": size, "page": page, "api_key": self.require_key()}
        )
        docs = data.get("docs", []) or []
        more = page * size < int(data.get("count") or 0) and bool(docs)
        return Page(
            records=[self._record(d) for d in docs],
            next_cursor=encode_cursor({"page": page + 1}) if more else None,
            searched=f"DPLA (live) for “{q}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not re.fullmatch(r"[0-9a-f]{32}", record_id):
            raise NotFound(record_id)
        data = self.get(f"{self.api}/{record_id}", {"api_key": self.require_key()})
        docs = data.get("docs") or []
        if not docs:
            raise NotFound(record_id)
        return self._record(docs[0])

    def _record(self, d: dict[str, Any]) -> ConnectorRecord:
        src = d.get("sourceResource", {}) or {}
        date = src.get("date")
        date_text = ""
        if isinstance(date, list) and date:
            date = date[0]
        if isinstance(date, dict):
            date_text = date.get("displayDate", "")
        provider = d.get("dataProvider")
        provider_name = provider.get("name", "") if isinstance(provider, dict) else _first(provider)
        rights = _first(d.get("rights")) or _first(src.get("rights"))
        return ConnectorRecord(
            connector=self.key,
            id=str(d.get("id", "")),
            title=_first(src.get("title")) or str(d.get("id", "")),
            description=_clip(_first(src.get("description"))),
            record_type=_first(src.get("type")),
            url=_first(d.get("isShownAt")),
            date_text=date_text,
            fields={k: v for k, v in {"held_by": provider_name, "rights": rights}.items() if v},
            rights=rights or "See the item for its rights",
            attribution=provider_name or "DPLA",
        )


# --- Geograph (photos of every grid square, CC BY-SA) ----------------------------------


class GeographConnector(LiveConnector):
    key = "geograph"
    name = "Geograph Britain and Ireland"
    source_key = "geograph"
    setting = "GEOGRAPH_API_KEY"
    setup_note = "Needs a Geograph API key (free, requested on their site)."
    storage = "reference_only"
    licence = "Photos CC BY-SA 2.0; credit the photographer and link the photo"
    attribution = "Photographer, via Geograph"
    description = (
        "Photos of places across Britain, most taken since 2005: what streets and "
        "buildings look like today and in recent decades. Search by place or grid reference."
    )
    api = "https://api.geograph.org.uk"
    max_page_size = 100

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        state = decode_cursor(cursor)
        params: dict[str, Any] = {"key": self.require_key(), "format": "JSON"}
        if state:
            # Later pages come from the saved search the first page created.
            search_id, page = state.get("i"), state.get("page")
            if not (isinstance(search_id, str) and search_id.isdigit() and isinstance(page, int)):
                raise BadQuery("Invalid cursor")
            params.update({"i": search_id, "page": page})
        else:
            params.update({"q": q, "perpage": size})
        data = self.get(f"{self.api}/syndicator.php", params)
        if data.get("error"):
            # e.g. "unable to identify a unique location": the query, not the service.
            raise BadQuery(str(data["error"]))
        items = data.get("items", []) or []
        found = re.search(r"/feed/results/(\d+)/(\d+)\.json", data.get("nextURL") or "")
        nxt = encode_cursor({"i": found[1], "page": int(found[2])}) if found and items else None
        return Page(
            records=[self._record(i) for i in items],
            next_cursor=nxt,
            searched=f"Geograph photos (live) for “{q}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not record_id.isdigit():
            raise NotFound(record_id)
        data = self.get(
            f"{self.api}/api/oembed",
            {
                "url": f"https://www.geograph.org.uk/photo/{record_id}",
                "format": "json",
                "key": self.require_key(),
            },
        )
        if not data.get("title"):
            raise NotFound(record_id)
        geo = data.get("geo") or {}
        return ConnectorRecord(
            connector=self.key,
            id=record_id,
            title=data["title"],
            description=_clip(_first(data.get("description"))),
            record_type="photo",
            url=data.get("web_page") or f"https://www.geograph.org.uk/photo/{record_id}",
            latitude=_float(geo.get("lat")),
            longitude=_float(geo.get("long")),
            fields={
                k: v
                for k, v in {
                    "photographer": data.get("author_name"),
                    "thumbnail": data.get("thumbnail_url"),
                    "grid_square": geo.get("square"),
                    "licence": data.get("license_url"),
                }.items()
                if v
            },
            rights=(
                f"{data.get('license') or 'CC BY-SA 2.0'}, © {data['author_name']}"
                if data.get("author_name")
                else data.get("license") or "CC BY-SA 2.0"
            ),
            attribution=(
                f"{data['author_name']}, via Geograph" if data.get("author_name") else "Geograph"
            ),
        )

    def _record(self, i: dict[str, Any]) -> ConnectorRecord:
        rid = str(i.get("guid") or "")
        author = _first(i.get("author"))
        return ConnectorRecord(
            connector=self.key,
            id=rid,
            title=_first(i.get("title")) or rid,
            description=_clip(_first(i.get("description"))),
            record_type="photo",
            url=_first(i.get("link")) or f"https://www.geograph.org.uk/photo/{rid}",
            date_text=_first(i.get("imageTaken")),
            latitude=_float(i.get("lat")),
            longitude=_float(i.get("long")),
            fields={
                k: v
                for k, v in {
                    "photographer": author,
                    "thumbnail": _first(i.get("thumb")),
                    "licence": _first(i.get("licence")),
                }.items()
                if v
            },
            rights=f"CC BY-SA 2.0, © {author}" if author else "CC BY-SA 2.0",
            attribution=f"{author}, via Geograph" if author else "Geograph",
        )


# --- The National Archives: Discovery (catalogue; nothing may be stored) ---------------


class TNADiscoveryConnector(LiveConnector):
    key = "tna-discovery"
    name = "The National Archives: Discovery"
    source_key = "tna-discovery"
    setting = "TNA_DISCOVERY_ENABLED"
    setup_note = (
        "Needs registration with The National Archives (email webmaster@"
        "nationalarchives.gov.uk with the server's IP address), then TNA_DISCOVERY_ENABLED."
    )
    storage = "none"  # API terms: "do not cache or store any content returned by the API"
    licence = "Catalogue descriptions; TNA API terms (no caching or storing)"
    attribution = "The National Archives' Discovery catalogue"
    description = (
        "Catalogue descriptions from The National Archives and about 2,500 other UK "
        "archives, including county record offices. Descriptions, not the documents."
    )
    api = "https://discovery.nationalarchives.gov.uk/API"
    min_interval = 1.0  # TNA asks for no more than one request a second
    max_page_size = 50

    @property
    def key_value(self) -> str:
        return "enabled" if getattr(settings, self.setting, False) is True else ""

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        page = _page_number(cursor)
        data = self.get(
            f"{self.api}/search/records",
            {"sps.searchQuery": q, "sps.resultsPageSize": size, "sps.page": page},
        )
        records = data.get("records", []) or []
        more = page * size < int(data.get("count") or 0) and bool(records)
        return Page(
            records=[self._record(r) for r in records],
            next_cursor=encode_cursor({"page": page + 1}) if more else None,
            searched=f"The National Archives' Discovery catalogue (live) for “{q}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not re.fullmatch(r"[A-Za-z0-9\-]{1,64}", record_id):
            raise NotFound(record_id)
        d = self.get(f"{self.api}/records/v1/details/{record_id}", {})
        if not d.get("id"):
            raise NotFound(record_id)
        held = d.get("heldBy") or []
        held_by = ", ".join(h.get("xReferenceName", "") for h in held if isinstance(h, dict))
        scope = d.get("scopeContent") or {}
        return ConnectorRecord(
            connector=self.key,
            id=d["id"],
            title=_first(d.get("title")) or d["id"],
            description=_clip(re.sub(r"<[^>]+>", " ", _first(scope.get("description")))),
            record_type="catalogue description",
            url=f"https://discovery.nationalarchives.gov.uk/details/r/{d['id']}",
            date_text=_first(d.get("coveringDates")),
            fields={
                k: v
                for k, v in {"reference": d.get("citableReference"), "held_by": held_by}.items()
                if v
            },
            rights="Catalogue description; see Discovery",
            attribution=held_by or "The National Archives",
        )

    def _record(self, r: dict[str, Any]) -> ConnectorRecord:
        held_by = ", ".join(r.get("heldBy") or [])
        return ConnectorRecord(
            connector=self.key,
            id=str(r.get("id", "")),
            title=_first(r.get("title")) or str(r.get("id", "")),
            description=_clip(re.sub(r"<[^>]+>", " ", _first(r.get("description")))),
            record_type="catalogue description",
            url=f"https://discovery.nationalarchives.gov.uk/details/r/{r.get('id', '')}",
            date_text=_first(r.get("coveringDates")),
            fields={
                k: v
                for k, v in {
                    "reference": r.get("reference"),
                    "held_by": held_by,
                    "context": _clip(_first(r.get("context")), 300),
                }.items()
                if v
            },
            rights="Catalogue description; see Discovery",
            attribution=held_by or "The National Archives",
        )

    def stored_label(self, record: ConnectorRecord) -> str:
        # Nothing returned by the API may be stored: keep only the link's own identifiers.
        return f"The National Archives' Discovery record {record.id}"


# --- OS Names (Ordnance Survey's gazetteer, OGL) ----------------------------------------


class OSNamesConnector(LiveConnector):
    key = "os-names"
    name = "OS Names (Ordnance Survey)"
    source_key = "ordnance-survey-opendata"
    setting = "OS_DATA_HUB_KEY"
    setup_note = "Needs an OS Data Hub API key (free plan)."
    storage = "full_copy"
    licence = "Open Government Licence"
    attribution = "Contains OS data © Crown copyright and database right"
    description = (
        "Today's place names, streets and postcodes across Great Britain, with locations. "
        "For finding where an address is now; it says nothing about the past."
    )
    api = "https://api.os.uk/search/names/v1/find"
    max_page_size = 100

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        offset = decode_cursor(cursor).get("offset", 0)
        if not isinstance(offset, int) or offset < 0:
            raise BadQuery("Invalid cursor")
        params: dict[str, Any] = {"query": q, "maxresults": size, "key": self.require_key()}
        if offset:
            params["offset"] = offset
        data = self.get(self.api, params)
        results = [r["GAZETTEER_ENTRY"] for r in data.get("results", []) if "GAZETTEER_ENTRY" in r]
        total = int((data.get("header") or {}).get("totalresults") or 0)
        more = offset + size < total and bool(results)
        return Page(
            records=[self._record(e) for e in results],
            next_cursor=encode_cursor({"offset": offset + size}) if more else None,
            searched=f"OS Names (live) for “{q}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        # OS Names has no lookup by ID, so the ID carries the name to search again.
        os_id, _, name = record_id.partition("~")
        if not os_id or not name:
            raise NotFound(record_id)
        page = self.search(name, page_size=100)
        for r in page.records:
            if r.id == record_id:
                return r
        raise NotFound(record_id)

    def _record(self, e: dict[str, Any]) -> ConnectorRecord:
        lat = lng = None
        x, y = _float(e.get("GEOMETRY_X")), _float(e.get("GEOMETRY_Y"))
        if x is not None and y is not None:
            lat, lng = bng_to_wgs84(x, y)
        where = ", ".join(
            v
            for v in (e.get("POPULATED_PLACE"), e.get("COUNTY_UNITARY"))
            if v and v != e.get("NAME1")
        )
        return ConnectorRecord(
            connector=self.key,
            id=f"{e.get('ID', '')}~{e.get('NAME1', '')}",
            title=e.get("NAME1", ""),
            description=", ".join(v for v in (e.get("LOCAL_TYPE"), where) if v),
            record_type=str(e.get("TYPE", "")).lower(),
            url=e.get("NAMES_URI", ""),
            latitude=round(lat, 6) if lat is not None else None,
            longitude=round(lng, 6) if lng is not None else None,
            fields={
                k: v
                for k, v in {
                    "postcode_district": e.get("POSTCODE_DISTRICT"),
                    "easting": x,
                    "northing": y,
                }.items()
                if v
            },
            rights="Open Government Licence",
            attribution=self.attribution,
        )


# --- British National Grid to WGS84 -----------------------------------------------------


# Transverse Mercator grids: ellipsoid (a, b), scale f0, true origin (degrees), false
# origin (e0, n0), and a position-vector Helmert to WGS84 (tx, ty, tz in metres; rx, ry,
# rz in arc seconds; scale in ppm).
BRITISH_GRID = {
    "a": 6377563.396, "b": 6356256.909, "f0": 0.9996012717,  # Airy 1830 (OSGB36)
    "lat0": 49.0, "lon0": -2.0, "e0": 400000.0, "n0": -100000.0,
    "helmert": (446.448, -125.157, 542.060, 0.1502, 0.2470, 0.8421, -20.4894),
}  # fmt: skip
IRISH_GRID = {
    "a": 6377340.189, "b": 6356034.447, "f0": 1.000035,  # Airy Modified 1849 (TM75)
    "lat0": 53.5, "lon0": -8.0, "e0": 200000.0, "n0": 250000.0,
    "helmert": (482.53, -130.596, 564.557, -1.042, -0.214, -0.631, 8.15),
}  # fmt: skip


def bng_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """OSGB36 (British National Grid) to WGS84 latitude/longitude (about 5 m)."""
    return grid_to_wgs84(easting, northing, BRITISH_GRID)


def irish_grid_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Irish Grid (TM75, EPSG:29902) to WGS84 latitude/longitude (a few metres)."""
    return grid_to_wgs84(easting, northing, IRISH_GRID)


def grid_to_wgs84(easting: float, northing: float, grid: dict) -> tuple[float, float]:
    """A Transverse Mercator grid reference to WGS84, via a Helmert transform.

    Formulae from Ordnance Survey's "A guide to coordinates systems in Great Britain".
    Good enough for placing a pin; not for surveying.
    """
    a, b, f0 = grid["a"], grid["b"], grid["f0"]
    lat0, lon0 = math.radians(grid["lat0"]), math.radians(grid["lon0"])
    n0, e0 = grid["n0"], grid["e0"]
    e2 = 1 - (b * b) / (a * a)
    n = (a - b) / (a + b)

    lat, m = lat0, 0.0
    while True:
        lat = (northing - n0 - m) / (a * f0) + lat
        dl, sl = lat - lat0, lat + lat0
        m = (
            b
            * f0
            * (
                (1 + n + 1.25 * n**2 + 1.25 * n**3) * dl
                - (3 * n + 3 * n**2 + 2.625 * n**3) * math.sin(dl) * math.cos(sl)
                + (1.875 * n**2 + 1.875 * n**3) * math.sin(2 * dl) * math.cos(2 * sl)
                - (35 / 24) * n**3 * math.sin(3 * dl) * math.cos(3 * sl)
            )
        )
        if abs(northing - n0 - m) < 0.00001:
            break

    sin_lat, cos_lat, tan_lat = math.sin(lat), math.cos(lat), math.tan(lat)
    nu = a * f0 / math.sqrt(1 - e2 * sin_lat**2)
    rho = a * f0 * (1 - e2) / (1 - e2 * sin_lat**2) ** 1.5
    eta2 = nu / rho - 1
    sec = 1 / cos_lat
    t2 = tan_lat**2
    vii = tan_lat / (2 * rho * nu)
    viii = tan_lat / (24 * rho * nu**3) * (5 + 3 * t2 + eta2 - 9 * t2 * eta2)
    ix = tan_lat / (720 * rho * nu**5) * (61 + 90 * t2 + 45 * t2**2)
    x_ = sec / nu
    xi = sec / (6 * nu**3) * (nu / rho + 2 * t2)
    xii = sec / (120 * nu**5) * (5 + 28 * t2 + 24 * t2**2)
    xiia = sec / (5040 * nu**7) * (61 + 662 * t2 + 1320 * t2**2 + 720 * t2**3)
    de = easting - e0
    phi = lat - vii * de**2 + viii * de**4 - ix * de**6
    lam = lon0 + x_ * de - xi * de**3 + xii * de**5 - xiia * de**7

    # Grid datum geodetic -> cartesian (height 0).
    nu_a = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    x1 = nu_a * math.cos(phi) * math.cos(lam)
    y1 = nu_a * math.cos(phi) * math.sin(lam)
    z1 = (1 - e2) * nu_a * math.sin(phi)

    # Helmert -> WGS84.
    tx, ty, tz, *rot, ppm = grid["helmert"]
    s = ppm * 1e-6
    rx, ry, rz = (math.radians(v / 3600) for v in rot)
    x2 = tx + (1 + s) * x1 - rz * y1 + ry * z1
    y2 = ty + rz * x1 + (1 + s) * y1 - rx * z1
    z2 = tz - ry * x1 + rx * y1 + (1 + s) * z1

    # Cartesian -> WGS84 geodetic (GRS80 ellipsoid).
    a2, b2 = 6378137.0, 6356752.3141
    e2b = 1 - (b2 * b2) / (a2 * a2)
    p = math.hypot(x2, y2)
    phi2 = math.atan2(z2, p * (1 - e2b))
    for _ in range(10):
        nu2 = a2 / math.sqrt(1 - e2b * math.sin(phi2) ** 2)
        phi2 = math.atan2(z2 + e2b * nu2 * math.sin(phi2), p)
    return math.degrees(phi2), math.degrees(math.atan2(y2, x2))


# --- Open sources (no key needed) --------------------------------------------------


class OpenConnector(LiveConnector):
    """A live source that needs no key; it's always set up."""

    @property
    def key_value(self) -> str:
        return "open"


_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _place_near(words: list[str]) -> tuple[str, tuple[float, float]] | None:
    """A place named in the query that we can locate (our places, then c.1900 map names)."""
    from connectors.models import DatasetRow
    from history.models import Place

    for w in words:
        p = Place.objects.filter(name__iexact=w, latitude__isnull=False).first()
        if p is not None:
            return w, (float(p.latitude), float(p.longitude))
    for w in words:
        row = (
            DatasetRow.objects.filter(dataset__key="old-map-names", title_lower=w.lower())
            .exclude(latitude__isnull=True)
            .first()
        )
        if row is not None:
            return w, (row.latitude, row.longitude)
    return None


class HistoricEnglandConnector(OpenConnector):
    key = "historic-england"
    name = "National Heritage List for England (Historic England)"
    source_key = "historic-england-nhle"
    storage = "full_copy"  # Open Government Licence
    licence = "Open Government Licence"
    attribution = (
        "© Historic England. Contains Ordnance Survey data © Crown copyright and database right"
    )
    description = (
        "Every listed building in England, with its grade, the date it was listed and an exact "
        "location (England only). Add a town to search near it, e.g. “High Street Ludlow”. "
        "The date is when "
        "it was listed, not when it was built."
    )
    api = (
        "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/"
        "National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer/0/query"
    )
    max_page_size = 100
    radius = 0.03  # degrees around a named town (about 2–3 km)

    def _query(self, where: str, extra: dict[str, Any]) -> dict[str, Any]:
        data = self.get(
            self.api,
            {
                "where": where,
                "outFields": "ListEntry,Name,Grade,ListDate,hyperlink",
                "outSR": 4326,
                "orderByFields": "ListEntry",
                "f": "json",
                **extra,
            },
        )
        if "error" in data:
            raise BadQuery(str(data["error"].get("message", "Search failed")))
        return data

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        offset = decode_cursor(cursor).get("offset", 0)
        if not isinstance(offset, int) or offset < 0:
            raise BadQuery("Invalid cursor")
        words = [w for w in re.findall(r"[A-Za-z0-9]+", q)]
        near = _place_near(words)
        extra: dict[str, Any] = {"resultOffset": offset, "resultRecordCount": size}
        if near:
            words = [w for w in words if w != near[0]]
            lat, lng = near[1]
            r = self.radius
            extra.update(
                {
                    "geometry": f"{lng - r},{lat - r},{lng + r},{lat + r}",
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": 4326,
                    "spatialRel": "esriSpatialRelIntersects",
                }
            )
        if not words and not near:
            raise BadQuery("Search for a building name, street or town")
        # Only letters and digits reach the query, so nothing can change its meaning.
        where = " AND ".join(f"UPPER(Name) LIKE '%{w.upper()}%'" for w in words) or "1=1"
        data = self._query(where, extra)
        features = data.get("features", []) or []
        more = bool(data.get("exceededTransferLimit")) and bool(features)
        where_text = f" near {near[0]}" if near else ""
        return Page(
            records=[self._record(f) for f in features],
            next_cursor=encode_cursor({"offset": offset + size}) if more else None,
            searched=f"the National Heritage List for England (live) for “{q}”{where_text}",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not record_id.isdigit():
            raise NotFound(record_id)
        features = self._query(f"ListEntry={int(record_id)}", {"resultRecordCount": 1}).get(
            "features"
        )
        if not features:
            raise NotFound(record_id)
        return self._record(features[0])

    def _record(self, f: dict[str, Any]) -> ConnectorRecord:
        a = f.get("attributes", {}) or {}
        points = (f.get("geometry") or {}).get("points") or [[None, None]]
        lng, lat = points[0][0], points[0][1]
        listed = ""
        if isinstance(a.get("ListDate"), int | float):
            # Listing dates can be before 1970, which time.gmtime rejects on Windows.
            listed = str((_EPOCH + timedelta(milliseconds=a["ListDate"])).year)
        grade = a.get("Grade") or ""
        entry = str(a.get("ListEntry", ""))
        return ConnectorRecord(
            connector=self.key,
            id=entry,
            title=a.get("Name") or entry,
            description=f"Grade {grade} listed building" if grade else "Listed building",
            record_type="listed building",
            url=a.get("hyperlink")
            or f"https://historicengland.org.uk/listing/the-list/list-entry/{entry}",
            date_text=f"Listed {listed}" if listed else "",
            latitude=_float(lat),
            longitude=_float(lng),
            fields={k: v for k, v in {"grade": grade, "list_entry": entry}.items() if v},
            rights="Open Government Licence",
            attribution=self.attribution,
        )


class GazetteConnector(OpenConnector):
    key = "the-gazette"
    name = "The Gazette (London, Edinburgh and Belfast)"
    source_key = "the-gazette"
    storage = "reference_only"
    licence = "Open Government Licence (not covering personal data)"
    attribution = "The Gazette, Crown copyright"
    description = (
        "The UK's official public record since 1665: military commissions and promotions, "
        "honours, bankruptcies, partnerships dissolved, deceased estates. Only notices at least "
        "100 years old are searched here."
    )
    api = "https://www.thegazette.co.uk/all-notices/notice/data.json"
    min_interval = 2.0  # The Gazette's fair use policy: at most 5 requests every 10 seconds
    max_page_size = 50
    min_age_years = 100

    def cutoff(self) -> str:
        return f"{time.gmtime().tm_year - self.min_age_years}-12-31"

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        page = _page_number(cursor)
        data = self.get(
            self.api,
            {
                "text": q,
                "results-page-size": size,
                "results-page": page,
                # Living people stay out by default (ADR-015): older notices only.
                "end-publish-date": self.cutoff(),
            },
        )
        entries = data.get("entry", []) or []
        total = int(data.get("f:total") or 0)
        more = page * size < total and bool(entries)
        return Page(
            records=[self._record(e) for e in entries],
            next_cursor=encode_cursor({"page": page + 1}) if more else None,
            searched=f"The Gazette (live) for “{q}”, notices published up to {self.cutoff()[:4]}",
        )

    PATH = re.compile(
        r"(notice/\d+|(London|Edinburgh|Belfast)/issue/\d+/(page|supplement)/\d+(/page/\d+)?)"
    )

    def get_record(self, record_id: str) -> ConnectorRecord:
        # Built from the ID without fetching: nothing beyond the link is shown.
        if not self.PATH.fullmatch(record_id):
            raise NotFound(record_id)
        parts = record_id.split("/")
        if parts[0] == "notice":
            title = f"Gazette notice {parts[1]}"
        else:
            title = f"The {parts[0]} Gazette, issue {parts[2]}, {parts[3]} {parts[4]}"
        return ConnectorRecord(
            connector=self.key,
            id=record_id,
            title=title,
            description="Open it on The Gazette to read the notice.",
            record_type="gazette notice",
            url=f"https://www.thegazette.co.uk/{record_id}",
            rights="Open Government Licence (not covering personal data)",
            attribution=self.attribution,
        )

    def _record(self, e: dict[str, Any]) -> ConnectorRecord:
        raw_id = str(e.get("id", ""))
        path = raw_id.split("thegazette.co.uk/", 1)[-1].removeprefix("id/")
        text = re.sub(r"<[^>]+>", " ", _first(e.get("content")))
        point = e.get("geo:Point") or {}
        category = (
            (e.get("category") or {}).get("@term", "")
            if isinstance(e.get("category"), dict)
            else ""
        )
        return ConnectorRecord(
            connector=self.key,
            id=path,
            title=" ".join(_first(e.get("title")).split()) or path,
            description=_clip(text.replace("…", "…")),
            record_type=(category or "gazette page").lower(),
            url=f"https://www.thegazette.co.uk/{path}",
            date_text=_first(e.get("published"))[:10],
            latitude=_float(point.get("geo:lat")),
            longitude=_float(point.get("geo:long")),
            rights="Open Government Licence (not covering personal data)",
            attribution=self.attribution,
        )


class GeoNamesConnector(LiveConnector):
    key = "geonames"
    name = "GeoNames"
    source_key = "geonames"
    setting = "GEONAMES_USERNAME"
    setup_note = "Needs a free GeoNames account name with web services switched on."
    storage = "full_copy"  # CC BY 4.0
    licence = "CC BY 4.0"
    attribution = "GeoNames (geonames.org)"
    description = (
        "Place names worldwide with other spellings and locations: towns, villages, farms, "
        "hills. Useful for finding where a place in an old record is."
    )
    api = "https://secure.geonames.org"
    max_page_size = 100

    def _check(self, data: dict[str, Any]) -> dict[str, Any]:
        status = data.get("status")
        if isinstance(status, dict):
            code = int(status.get("value", 0))
            if code == 10:
                raise AccessDenied(str(status.get("message")))
            if code in (18, 19, 20):
                raise RateLimited(str(status.get("message")))
            if code in (11, 15):
                raise NotFound(str(status.get("message")))
            raise BadQuery(str(status.get("message", "Search failed")))
        return data

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        offset = decode_cursor(cursor).get("offset", 0)
        if not isinstance(offset, int) or offset < 0:
            raise BadQuery("Invalid cursor")
        data = self._check(
            self.get(
                f"{self.api}/searchJSON",
                {
                    "q": q,
                    "maxRows": size,
                    "startRow": offset,
                    "style": "MEDIUM",
                    "username": self.require_key(),
                },
            )
        )
        places = data.get("geonames", []) or []
        total = int(data.get("totalResultsCount") or 0)
        more = offset + size < total and bool(places)
        return Page(
            records=[self._record(p) for p in places],
            next_cursor=encode_cursor({"offset": offset + size}) if more else None,
            searched=f"GeoNames (live) for “{q}”",
        )

    def nearest_place(self, lat: float, lng: float) -> str | None:
        """The nearest populated place (towns and villages of 1,000 or more)."""
        data = self._check(
            self.get(
                f"{self.api}/findNearbyPlaceNameJSON",
                {"lat": lat, "lng": lng, "cities": "cities1000", "username": self.require_key()},
            )
        )
        places = data.get("geonames") or []
        return places[0].get("name") if places else None

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not record_id.isdigit():
            raise NotFound(record_id)
        data = self._check(
            self.get(
                f"{self.api}/getJSON",
                {"geonameId": record_id, "username": self.require_key()},
            )
        )
        if not data.get("geonameId"):
            raise NotFound(record_id)
        return self._record(data)

    def _record(self, p: dict[str, Any]) -> ConnectorRecord:
        gid = str(p.get("geonameId", ""))
        where = ", ".join(v for v in (p.get("adminName1"), p.get("countryName")) if v)
        return ConnectorRecord(
            connector=self.key,
            id=gid,
            title=p.get("name") or p.get("toponymName") or gid,
            description=", ".join(v for v in (p.get("fcodeName"), where) if v),
            record_type=str(p.get("fclName") or "place"),
            url=f"https://www.geonames.org/{gid}",
            latitude=_float(p.get("lat")),
            longitude=_float(p.get("lng")),
            fields={
                k: v
                for k, v in {
                    "population": p.get("population"),
                    "country": p.get("countryCode"),
                }.items()
                if v
            },
            rights="CC BY 4.0",
            attribution=self.attribution,
        )


# --- Museums and research (open, no key) ---------------------------------------------


class MetMuseumConnector(OpenConnector):
    key = "met-museum"
    name = "The Metropolitan Museum of Art"
    source_key = "met-museum"
    storage = "full_copy"  # Open Access data is CC0
    licence = "Data CC0; images only for public-domain objects"
    attribution = "The Metropolitan Museum of Art"
    description = (
        "Nearly 500,000 objects: paintings, photographs, clothing, tools and everyday things. "
        "Useful for showing what objects of a period looked like."
    )
    api = "https://collectionapi.metmuseum.org/public/collection"
    max_page_size = 20  # each result needs its own request

    def search(self, query: str, cursor: str | None = None, page_size: int = 10) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        offset = decode_cursor(cursor).get("offset", 0)
        if not isinstance(offset, int) or offset < 0 or offset + size > 10000:
            raise BadQuery("Invalid cursor")
        data = self.get(f"{self.api}/v1.1/search", {"q": q, "offset": offset, "limit": size})
        ids = data.get("objectIDs") or []
        records = []
        for object_id in ids:
            try:
                records.append(self.get_record(str(object_id)))
            except NotFound:
                continue  # withdrawn objects are listed but no longer served
        total = int(data.get("total") or 0)
        more = offset + size < min(total, 10000) and bool(ids)
        return Page(
            records=records,
            next_cursor=encode_cursor({"offset": offset + size}) if more else None,
            searched=f"The Met's collection (live) for “{q}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not record_id.isdigit():
            raise NotFound(record_id)
        o = self.get(f"{self.api}/v1/objects/{record_id}", {})
        if not o.get("objectID"):
            raise NotFound(record_id)
        public = bool(o.get("isPublicDomain"))
        return ConnectorRecord(
            connector=self.key,
            id=str(o["objectID"]),
            title=o.get("title") or o.get("objectName") or record_id,
            description=", ".join(
                v for v in (o.get("objectName"), o.get("artistDisplayName"), o.get("medium")) if v
            ),
            record_type=(o.get("objectName") or "object").lower(),
            url=o.get("objectURL") or "",
            date_text=o.get("objectDate") or "",
            fields={
                k: v
                for k, v in {
                    "department": o.get("department"),
                    "culture": o.get("culture"),
                    "country": o.get("country"),
                    "credit": o.get("creditLine"),
                    # Images only where the object is public domain.
                    "image": o.get("primaryImageSmall") if public else None,
                }.items()
                if v
            },
            rights="Public domain (CC0)" if public else "Data CC0; image rights reserved",
            attribution=self.attribution,
        )


class ArtInstituteChicagoConnector(OpenConnector):
    key = "art-institute-chicago"
    name = "Art Institute of Chicago"
    source_key = "art-institute-chicago"
    storage = "full_copy"  # CC0, except descriptions (CC BY), which we don't request
    licence = "Data CC0 (descriptions CC BY, not used); images only for public-domain works"
    attribution = "Art Institute of Chicago"
    description = "Around 130,000 artworks and objects, many public domain with images."
    api = "https://api.artic.edu/api/v1/artworks"
    fields_wanted = (
        "id,title,date_display,artist_display,place_of_origin,medium_display,"
        "artwork_type_title,is_public_domain,image_id,credit_line"
    )
    max_page_size = 50

    def _headers(self) -> dict[str, str]:
        # The Art Institute asks clients to identify themselves this way.
        return {"AIC-User-Agent": "ArchiveHub (https://github.com/Discern-AI/ArchiveHub)"}

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        page = _page_number(cursor)
        data = self.get(
            f"{self.api}/search",
            {"q": q, "limit": size, "page": page, "fields": self.fields_wanted},
            headers=self._headers(),
        )
        iiif = (data.get("config") or {}).get("iiif_url", "")
        items = data.get("data", []) or []
        pages = int((data.get("pagination") or {}).get("total_pages") or 0)
        return Page(
            records=[self._record(a, iiif) for a in items],
            next_cursor=encode_cursor({"page": page + 1}) if page < pages and items else None,
            searched=f"The Art Institute of Chicago's collection (live) for “{q}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not record_id.isdigit():
            raise NotFound(record_id)
        data = self.get(
            f"{self.api}/{record_id}", {"fields": self.fields_wanted}, headers=self._headers()
        )
        if not (data.get("data") or {}).get("id"):
            raise NotFound(record_id)
        return self._record(data["data"], (data.get("config") or {}).get("iiif_url", ""))

    def _record(self, a: dict[str, Any], iiif: str) -> ConnectorRecord:
        public = bool(a.get("is_public_domain"))
        image = (
            f"{iiif}/{a['image_id']}/full/400,/0/default.jpg"
            if public and iiif and a.get("image_id")
            else None
        )
        rid = str(a.get("id", ""))
        return ConnectorRecord(
            connector=self.key,
            id=rid,
            title=a.get("title") or rid,
            description=", ".join(
                v
                for v in (
                    a.get("artwork_type_title"),
                    _first(a.get("artist_display")).replace("\n", " "),
                )
                if v
            ),
            record_type=(a.get("artwork_type_title") or "artwork").lower(),
            url=f"https://www.artic.edu/artworks/{rid}",
            date_text=a.get("date_display") or "",
            fields={
                k: v
                for k, v in {
                    "place": a.get("place_of_origin"),
                    "medium": a.get("medium_display"),
                    "credit": a.get("credit_line"),
                    "image": image,
                }.items()
                if v
            },
            rights="Public domain (CC0)" if public else "Data CC0; image rights reserved",
            attribution=self.attribution,
        )


class OpenAlexConnector(OpenConnector):
    key = "openalex"
    name = "OpenAlex (research papers and books)"
    source_key = "openalex"
    setting = "OPENALEX_API_KEY"  # optional: raises the daily budget
    storage = "full_copy"  # CC0 metadata
    licence = "Metadata CC0; each work has its own rights"
    attribution = "OpenAlex"
    description = (
        "Over 250 million scholarly works: journal articles, books and theses, including local "
        "and family history research. Metadata and links, not full text."
    )
    api = "https://api.openalex.org/works"
    max_page_size = 50

    def _params(self, extra: dict[str, Any]) -> dict[str, Any]:
        key = getattr(settings, self.setting, "")
        return {**extra, **({"api_key": key} if isinstance(key, str) and key else {})}

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        q = _require_query(query, self.name)
        size = _size(page_size, self.max_page_size)
        page = _page_number(cursor)
        data = self.get(self.api, self._params({"search": q, "per-page": size, "page": page}))
        works = data.get("results", []) or []
        total = int((data.get("meta") or {}).get("count") or 0)
        more = page * size < min(total, 10000) and bool(works)
        return Page(
            records=[self._record(w) for w in works],
            next_cursor=encode_cursor({"page": page + 1}) if more else None,
            searched=f"OpenAlex (live) for “{q}”",
        )

    def get_record(self, record_id: str) -> ConnectorRecord:
        if not re.fullmatch(r"W\d+", record_id):
            raise NotFound(record_id)
        return self._record(self.get(f"{self.api}/{record_id}", self._params({})))

    def _record(self, w: dict[str, Any]) -> ConnectorRecord:
        rid = str(w.get("id", "")).rsplit("/", 1)[-1]
        authors = [
            (a.get("author") or {}).get("display_name", "")
            for a in (w.get("authorships") or [])[:4]
        ]
        location = w.get("primary_location") or {}
        venue = (location.get("source") or {}).get("display_name", "")
        oa = (w.get("open_access") or {}).get("oa_url")
        return ConnectorRecord(
            connector=self.key,
            id=rid,
            title=w.get("display_name") or rid,
            description=", ".join(v for v in (", ".join(a for a in authors if a), venue) if v),
            record_type=str(w.get("type") or "work"),
            url=w.get("doi") or location.get("landing_page_url") or f"https://openalex.org/{rid}",
            date_text=str(w.get("publication_year") or ""),
            fields={k: v for k, v in {"free_to_read": oa, "published_in": venue}.items() if v},
            rights="Metadata CC0; see the work for its rights",
            attribution="OpenAlex",
        )


LIVE_CONNECTORS: tuple[LiveConnector, ...] = (
    EuropeanaConnector(),
    TNADiscoveryConnector(),
    GeographConnector(),
    OSNamesConnector(),
    DigitalNZConnector(),
    TroveConnector(),
    DPLAConnector(),
    HistoricEnglandConnector(),
    GazetteConnector(),
    GeoNamesConnector(),
    MetMuseumConnector(),
    ArtInstituteChicagoConnector(),
    OpenAlexConnector(),
)
