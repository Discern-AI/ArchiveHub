"""Search across everything this person may see (SPEC §5, Search).

Every search returns what was searched and what wasn't, so an empty result is never
taken as proof that something doesn't exist. Private content comes only from projects
and chats the person can see; each group says whether it is public or private.

Matching: every word must appear (case-insensitive) in one of the group's fields.
This runs the same on SQLite and Postgres; ranked full-text and vector search come
when hosted datasets need them (ADR-033).
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from dataclasses import asdict, dataclass, field
from functools import reduce
from operator import and_, or_
from typing import Any

from django.db.models import Q

from archive.models import Derivative, FileAsset, FileKind
from connectors.base import ConnectorError
from connectors.models import DatasetRow
from connectors.sources import get_connector
from history.models import Organisation, Person, Place, Source, SourceRecord
from history.queries import terms
from interviews.models import Segment
from projects.permissions import visible_chats, visible_projects
from timemap.models import MapItem

PER_GROUP = 8
COUNT_CAP = 50
SNIPPET = 90


@dataclass
class Result:
    id: str
    title: str
    snippet: str = ""
    date: str = ""
    place: str = ""
    source: str = ""
    link: str = ""
    url: str = ""
    project_title: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Group:
    key: str
    label: str
    layer: str  # public | private
    searched: str  # what exactly was looked at
    results: list[Result]
    count: int
    more: bool
    live: bool = False  # searched on an outside service just now
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["results"] = [asdict(r) for r in self.results]
        return data


# Things people can search for that aren't here yet, said plainly.
NOT_SEARCHED = [
    {
        "label": "Forum threads",
        "reason": "Forums haven't opened yet. They arrive with moderation tools.",
    },
    {
        "label": "People and services",
        "reason": "The directory of historians, researchers and services isn't open yet.",
    },
    {
        "label": "Museum collections (the Met, Art Institute of Chicago)",
        "reason": "Each result needs its own request, so they're searched in the Archive "
        "Explorer or by the assistant.",
    },
    {
        "label": "Sources we only link to",
        "reason": "Their records aren't held here. The source directory shows where to look.",
    },
]


def every_word(words: list[str], fields: list[str]) -> Q:
    """Each word must appear in at least one of the fields."""
    return reduce(and_, (reduce(or_, (Q(**{f"{f}__icontains": w}) for f in fields)) for w in words))


def snippet(text: str, words: list[str]) -> str:
    """A short extract around the first matching word, on word boundaries."""
    if not text:
        return ""
    low = text.lower()
    hits = [low.find(w) for w in words if low.find(w) >= 0]
    if not hits:
        return text[: SNIPPET * 2].strip() + ("…" if len(text) > SNIPPET * 2 else "")
    at = min(hits)
    start, end = max(0, at - SNIPPET), min(len(text), at + SNIPPET)
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    while end < len(text) and not text[end].isspace():
        end += 1
    out = " ".join(text[start:end].split())
    return ("…" if start > 0 else "") + out + ("…" if end < len(text) else "")


def _group(key, label, layer, searched, qs, to_result: Callable[[Any], Result]) -> Group:
    rows = list(qs[: COUNT_CAP + 1])
    count = min(len(rows), COUNT_CAP)
    return Group(
        key=key,
        label=label,
        layer=layer,
        searched=searched,
        results=[to_result(r) for r in rows[:PER_GROUP]],
        count=count,
        more=len(rows) > PER_GROUP,
    )


# --- Public reference content ----------------------------------------------------------


def _places(words) -> Group:
    qs = (
        Place.objects.select_related("parent")
        .filter(every_word(words, ["name", "alt_names"]))
        .order_by("name")
    )
    return _group(
        "places",
        "Places",
        "public",
        "Place names and other names",
        qs,
        lambda p: Result(
            id=f"place:{p.key}",
            title=str(p),
            snippet=p.note,
            link=f"/map?place={p.key}" if p.latitude is not None else "",
            extra={"on_map": p.latitude is not None, "precision": p.geocode_precision},
        ),
    )


def _organisations(words) -> Group:
    qs = (
        Organisation.objects.select_related("place", "place__parent")
        .filter(every_word(words, ["name", "alt_names", "kind"]))
        .order_by("name")
    )
    return _group(
        "organisations",
        "Pubs, businesses and organisations",
        "public",
        "Names, other names and kinds",
        qs,
        lambda o: Result(
            id=f"organisation:{o.key}",
            title=o.name,
            snippet=", ".join(o.alt_names),
            place=str(o.place) if o.place else "",
            source=o.kind,
            link=f"/map?place={o.place.key}" if o.place and o.place.latitude is not None else "",
        ),
    )


def _records(words) -> Group:
    qs = (
        SourceRecord.objects.select_related("source", "place", "place__parent")
        .filter(every_word(words, ["title", "summary", "record_type", "place__name"]))
        .order_by("title")
    )
    return _group(
        "records",
        "Checked records",
        "public",
        "ArchiveHub's checked records: titles and our summaries",
        qs,
        lambda r: Result(
            id=f"record:{r.key}",
            title=r.title,
            snippet=snippet(r.summary, words),
            date=r.date_display,
            place=str(r.place) if r.place else "",
            source=r.source.name,
            url=r.url,
            extra={"connector": "checked-reference", "record_id": r.key},
        ),
    )


def _map_names(words) -> Group:
    # Titles are stored lower-cased and indexed; all words must appear in the name.
    qs = DatasetRow.objects.filter(dataset__key="old-map-names").filter(
        reduce(and_, (Q(title_lower__contains=w) for w in words))
    )
    qs = qs.order_by("title_lower")
    return _group(
        "map_names",
        "Names on the c.1900 map",
        "public",
        "Old map names (OS six-inch, c.1900), Newbury and West Berkshire",
        qs,
        lambda r: Result(
            id=f"name:{r.external_id}",
            title=r.title,
            date="c.1888–1913",
            source="Old map names (OS six-inch, c.1900)",
            extra={
                "connector": "old-map-names",
                "record_id": r.external_id,
                "latitude": r.latitude,
                "longitude": r.longitude,
            },
        ),
    )


def _directory(words) -> Group:
    fields = ["name", "holder", "description", "coverage_area", "record_types", "tags"]
    qs = Source.objects.filter(every_word(words, fields)).order_by("name")
    return _group(
        "sources",
        "Source directory",
        "public",
        "Names, holders, descriptions, coverage and record types of listed sources",
        qs,
        lambda s: Result(
            id=f"source:{s.key}",
            title=s.name,
            snippet=snippet(s.description, words),
            source=s.get_access_type_display(),
            url=s.url,
            extra={"access_type": s.access_type, "licence": s.licence},
        ),
    )


# --- Private content: only from projects and chats this person can see -----------------


def _files(user, words) -> Group:
    projects = visible_projects(user)
    texts = Derivative.objects.filter(kind="text", file__project__in=projects).filter(
        every_word(words, ["text"])
    )
    qs = (
        FileAsset.objects.filter(project__in=projects)
        .filter(every_word(words, ["name"]) | Q(id__in=texts.values("file_id")))
        .select_related("project")
        .order_by("-created_at")
    )

    def result(f: FileAsset) -> Result:
        text = next((d.text for d in texts.filter(file=f)[:1]), "")
        return Result(
            id=f"file:{f.id}",
            title=f.name,
            snippet=snippet(text, words),
            source=f.get_kind_display(),
            link=f"/archive?project={f.project_id}&file={f.id}",
            project_title=f.project.title,
            extra={"is_photo": f.kind == FileKind.IMAGE},
        )

    return _group(
        "files",
        "Your Archive: files and photos",
        "private",
        "File names and text read from your files",
        qs,
        result,
    )


def _transcripts(user, words) -> Group:
    qs = (
        Segment.objects.filter(session__chat__in=visible_chats(user))
        .filter(every_word(words, ["text", "speaker"]))
        .select_related("session", "session__chat__project")
        .order_by("session__created_at", "line")
    )
    return _group(
        "interviews",
        "Interview transcripts",
        "private",
        "Every line of your interviews",
        qs,
        lambda g: Result(
            id=f"line:{g.session_id}:{g.line}",
            title=f"{g.session.narrator}, line {g.line}",
            snippet=snippet(g.text, words),
            source="Interview",
            link=f"/interviews/{g.session_id}#line-{g.line}",
            project_title=g.session.chat.project.title if g.session.chat.project else "",
        ),
    )


def _map_items(user, words) -> Group:
    qs = (
        MapItem.objects.filter(project__in=visible_projects(user))
        .filter(every_word(words, ["title", "text", "location_note", "date_text"]))
        .select_related("project")
        .order_by("year_from", "title")
    )
    return _group(
        "map_items",
        "Your memories and map items",
        "private",
        "Titles, words and location notes of items you've put on the map",
        qs,
        lambda i: Result(
            id=f"item:{i.id}",
            title=i.title,
            snippet=snippet(i.text, words),
            date=i.date_display,
            place=i.location_note,
            source=i.get_kind_display(),
            link=f"/map?item={i.id}&lat={i.latitude}&lng={i.longitude}",
            project_title=i.project.title,
        ),
    )


def _people(user, words) -> Group:
    qs = (
        Person.objects.filter(project__in=visible_projects(user))
        .filter(every_word(words, ["name", "alt_names"]))
        .select_related("project")
        .order_by("name")
    )
    return _group(
        "people",
        "People in your family trees",
        "private",
        "Names in your projects' family trees",
        qs,
        lambda p: Result(
            id=f"person:{p.id}",
            title=p.name,
            date=" – ".join(x for x in [p.birth_text, p.death_text] if x),
            source="Living: private" if p.living_status != "deceased" else "Family tree",
            link=f"/projects/{p.project_id}/people/{p.id}",
            project_title=p.project.title,
        ),
    )


def _explanations(words) -> Group:
    """Checked explanations of old terms and map abbreviations (history/glossary.py)."""
    from history.glossary import abbreviation, search_terms

    query = " ".join(words)
    results = [
        Result(
            id=f"term:{t['key']}",
            title=t["term"],
            snippet=t["meaning"],
            source=t["sources"][0]["title"],
            url=t["sources"][0]["url"],
            extra={"kind": t["kind"]},
        )
        for t in search_terms(query, limit=PER_GROUP)
    ]
    if len(words) == 1:
        abbr = abbreviation(words[0].upper()) or abbreviation(words[0])
        if abbr:
            results.insert(
                0,
                Result(
                    id=f"abbr:{abbr['abbr']}",
                    title=f"{abbr['abbr']} on Ordnance Survey maps",
                    snippet=abbr["text"].capitalize(),
                    source=abbr["source"],
                    url=abbr["source_url"],
                ),
            )
    return Group(
        key="explanations",
        label="Explanations of old terms",
        layer="public",
        searched=(
            "ArchiveHub's checked explanations of old money, Poor Law terms and map abbreviations"
        ),
        results=results,
        count=len(results),
        more=False,
    )


PUBLIC_GROUPS = [_places, _organisations, _records, _map_names, _directory, _explanations]
PRIVATE_GROUPS = [_map_items, _files, _transcripts, _people]


# Outside sources Search can ask at once, each with a single request (ADR-037).
LIVE_SEARCH = [
    "the-gazette",
    "historic-england",
    "tna-discovery",
    "openalex",
    "europeana",
    "wikidata",
    "geograph",
    "digitalnz",
    "trove",
    "dpla",
]
LIVE_PER_SOURCE = 5
LIVE_TIMEOUT = 12.0  # seconds for all outside sources together


def _live_group(connector, query: str) -> Group:
    from django.db import close_old_connections

    try:
        page = connector.search(query, page_size=LIVE_PER_SOURCE)
    except ConnectorError as exc:
        return Group(
            key=f"live:{connector.key}",
            label=connector.name,
            layer="public",
            searched=f"{connector.name} (live)",
            results=[],
            count=0,
            more=False,
            live=True,
            error=exc.user_message,
        )
    finally:
        close_old_connections()  # this runs in a worker thread
    return Group(
        key=f"live:{connector.key}",
        label=connector.name,
        layer="public",
        searched=page.searched or f"{connector.name} (live)",
        results=[
            Result(
                id=f"{connector.key}:{r.id}",
                title=r.title,
                snippet=r.description,
                date=r.date_text,
                source=r.attribution or connector.name,
                url=r.url,
                extra={
                    "connector": connector.key,
                    "record_id": r.id,
                    "rights": r.rights,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                },
            )
            for r in page.records
        ],
        count=len(page.records),
        more=bool(page.next_cursor),
        live=True,
    )


def search_live(query: str) -> tuple[list[Group], list[dict[str, str]]]:
    """Ask every set-up outside source at once; say which weren't set up or didn't answer."""
    chosen, not_set_up = [], []
    for key in LIVE_SEARCH:
        connector = get_connector(key)
        if hasattr(connector, "configured") and not connector.configured():
            not_set_up.append({"label": connector.name, "reason": "Not set up on this server yet."})
        else:
            chosen.append(connector)
    groups: dict[str, Group] = {}
    pool = ThreadPoolExecutor(max_workers=min(8, len(chosen) or 1))
    futures = {pool.submit(_live_group, c, query): c for c in chosen}
    try:
        for future in as_completed(futures, timeout=LIVE_TIMEOUT):
            group = future.result()
            groups[group.key] = group
    except TimeoutError:
        pass
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    ordered = []
    for c in chosen:
        ordered.append(
            groups.get(f"live:{c.key}")
            or Group(
                key=f"live:{c.key}",
                label=c.name,
                layer="public",
                searched=f"{c.name} (live)",
                results=[],
                count=0,
                more=False,
                live=True,
                error="Didn't answer in time.",
            )
        )
    return ordered, not_set_up


def search_everything(user, query: str, live: bool = False) -> dict[str, Any]:
    words = terms(query)
    not_searched = list(NOT_SEARCHED)
    if not live:
        not_searched.insert(
            0,
            {
                "label": "Outside sources (The Gazette, Historic England and others)",
                "reason": "Only when you tick “Also search outside sources”, because your "
                "search words are sent to them.",
            },
        )
    if not words:
        return {"query": query, "words": [], "groups": [], "not_searched": not_searched}
    groups = [g(words) for g in PUBLIC_GROUPS] + [g(user, words) for g in PRIVATE_GROUPS]
    if live:
        live_groups, not_set_up = search_live(query.strip()[:200])
        groups += live_groups
        not_searched = not_set_up + not_searched
    return {
        "query": query,
        "words": words,
        "groups": [g.to_dict() for g in groups],
        "not_searched": not_searched,
    }
