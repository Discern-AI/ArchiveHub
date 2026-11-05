"""Tools the assistant can call (SPEC §6), and the server-side record of what they did.

Each reply gets a ToolKit. It numbers every record or source a tool returns, so the model
cites [1], [2] … and the server, not the model, decides what those numbers link to
(ADR-020). It also keeps the "What I checked" list from the actual calls.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from asgiref.sync import sync_to_async
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from history import queries
from history.models import AccessType, Cost, Source, SourceRecord

# --- Tool input schemas ----------------------------------------------------------


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchDirectoryInput(_Input):
    query: str = Field(min_length=1, max_length=200)
    record_type: str | None = Field(default=None, max_length=100)


class SearchRecordsInput(_Input):
    query: str = Field(min_length=1, max_length=200)
    year_from: int | None = Field(default=None, ge=1000, le=2100)
    year_to: int | None = Field(default=None, ge=1000, le=2100)


class GetRecordInput(_Input):
    record_id: str = Field(min_length=1, max_length=64)


class CompareClaimsInput(_Input):
    subject: str = Field(min_length=1, max_length=200)
    predicate: str | None = Field(default=None, max_length=60)


def _schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    schema["additionalProperties"] = False
    return schema


TOOL_SPECS: list[tuple[str, str, type[BaseModel]]] = [
    (
        "search_source_directory",
        "Search ArchiveHub's directory of historical sources: archives, databases, websites "
        "and services, including ones that can't be searched from here. Use it to find out "
        "what exists, who holds it, whether it's free or paid, and how to access it. Returns "
        "numbered entries to cite.",
        SearchDirectoryInput,
    ),
    (
        "search_records",
        "Search the historical records ArchiveHub holds or has checked (currently a small, "
        "hand-checked set for Cheap Street and central Newbury). Optionally limit by year. "
        "Returns numbered records with our summary of what each says, to cite.",
        SearchRecordsInput,
    ),
    (
        "get_record",
        "Get the full details of one record returned by search_records or compare_claims, "
        "using its record_id.",
        GetRecordInput,
    ),
    (
        "compare_claims",
        "Look up a person, place or organisation by name and list every claim the records "
        "make about it, grouped by question (e.g. address), with the evidence for each and "
        "whether sources disagree. Use this before stating facts about a subject.",
        CompareClaimsInput,
    ),
]

TOOL_LABELS = {
    "search_source_directory": "Searching the source directory",
    "search_records": "Searching records",
    "get_record": "Reading a record",
    "compare_claims": "Comparing what the sources say",
}


def tool_definitions() -> list[dict[str, Any]]:
    """Constant across requests: changing tools mid-conversation breaks caching."""
    # Inputs stream as they're generated; every input is validated in ToolKit.run.
    return [
        {
            "name": name,
            "description": desc,
            "input_schema": _schema(model),
            "eager_input_streaming": True,
        }
        for name, desc, model in TOOL_SPECS
    ]


# --- Citations and the "What I checked" log ---------------------------------------


@dataclass
class Citation:
    n: int
    kind: str  # "record" or "source"
    id: str
    label: str
    url: str
    source: str


@dataclass
class ToolKit:
    user: Any
    citations: dict[tuple[str, str], Citation] = field(default_factory=dict)
    checked: list[dict[str, str]] = field(default_factory=list)

    # Numbering --------------------------------------------------------------------

    def cite(self, kind: str, obj_id: str, label: str, url: str, source: str) -> int:
        key = (kind, obj_id)
        if key not in self.citations:
            self.citations[key] = Citation(
                len(self.citations) + 1, kind, obj_id, label, url, source
            )
        return self.citations[key].n

    def cite_record(self, r: SourceRecord) -> int:
        return self.cite("record", str(r.id), r.title, r.url, r.source.name)

    def cite_source(self, s: Source) -> int:
        return self.cite("source", str(s.id), s.name, s.url, s.holder or s.name)

    def log(self, status: str, text: str) -> None:
        entry = {"status": status, "text": text}
        if entry not in self.checked:
            self.checked.append(entry)

    def cited_in(self, text: str) -> list[dict[str, Any]]:
        """Only numbers a tool actually returned, in the order first cited."""
        by_n = {c.n: c for c in self.citations.values()}
        seen: list[int] = []
        for group in re.findall(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]", text):
            for n in re.findall(r"\d+", group):
                if int(n) in by_n and int(n) not in seen:
                    seen.append(int(n))
        return [
            {
                "n": n,
                "kind": by_n[n].kind,
                "id": by_n[n].id,
                "label": by_n[n].label,
                "url": by_n[n].url,
                "source": by_n[n].source,
            }
            for n in seen
        ]

    # Running tools ----------------------------------------------------------------

    def label(self, name: str, tool_input: dict[str, Any]) -> str:
        base = TOOL_LABELS.get(name, "Working")
        q = tool_input.get("query") or tool_input.get("subject")
        return f"{base}: “{q}”" if q else base

    async def arun(self, name: str, tool_input: Any) -> tuple[str, bool]:
        return await sync_to_async(self.run, thread_sensitive=True)(name, tool_input)

    def run(self, name: str, tool_input: Any) -> tuple[str, bool]:
        spec = {n: m for n, _, m in TOOL_SPECS}.get(name)
        if spec is None:
            return json.dumps({"error": f"Unknown tool {name}"}), True
        try:
            args = spec.model_validate(tool_input)
        except ValidationError as exc:
            return json.dumps(
                {"error": "INVALID_INPUT", "detail": exc.errors()[:3]}, default=str
            ), True
        result = getattr(self, f"_{name}")(args)
        return json.dumps(result, ensure_ascii=False, default=str), False

    # Tools ------------------------------------------------------------------------

    def _search_source_directory(self, args: SearchDirectoryInput) -> dict[str, Any]:
        sources = queries.search_sources(args.query, args.record_type)
        self.log("Searched", f"The source directory for “{args.query}” ({len(sources)} found)")
        out = []
        unreachable = 0
        for s in sources:
            if s.access_type == AccessType.EXTERNAL_ONLY and unreachable < 4:
                unreachable += 1
                cost = "" if s.cost == Cost.UNKNOWN else f", {s.get_cost_display().lower()}"
                self.log("Couldn't access", f"{s.name} (not connected here{cost})")
            out.append(
                {
                    "cite": self.cite_source(s),
                    "name": s.name,
                    "holder": s.holder,
                    "what_it_holds": s.description,
                    "coverage": s.coverage_area,
                    "period": _period(s.period_from, s.period_to),
                    "record_types": s.record_types,
                    "access": s.get_access_type_display(),
                    "cost": s.get_cost_display(),
                    "conditions": s.conditions,
                    "url": s.url or None,
                }
            )
        return {"results": out, "note": "Entries describe sources; they are not records."}

    def _search_records(self, args: SearchRecordsInput) -> dict[str, Any]:
        records = queries.search_records(args.query, args.year_from, args.year_to)
        when = _period(args.year_from, args.year_to)
        scope = f"for “{args.query}”" + (f", {when}" if when else "")
        if records:
            self.log("Searched", f"ArchiveHub's checked records {scope} ({len(records)} found)")
        else:
            self.log("Not found", f"No records in ArchiveHub {scope}")
        return {
            "results": [_record_brief(self, r) for r in records],
            "coverage_note": "ArchiveHub currently holds a small checked set for Cheap Street "
            "and central Newbury. Not finding something here doesn't mean it doesn't exist.",
        }

    def _get_record(self, args: GetRecordInput) -> dict[str, Any]:
        record = (
            SourceRecord.objects.select_related("source", "place").filter(id=args.record_id).first()
            if _is_uuid(args.record_id)
            else None
        )
        if record is None:
            return {"error": "No record with that id. Use an id returned by another tool."}
        self.log("Read", record.title)
        detail = _record_brief(self, record)
        detail.update(
            {
                "fields": record.fields,
                "checked_on": str(record.checked_on or ""),
                "storage": record.get_storage_display(),
            }
        )
        return detail

    def _compare_claims(self, args: CompareClaimsInput) -> dict[str, Any]:
        subjects = queries.find_subjects(args.subject)
        if not subjects:
            self.log("Not found", f"Nothing in ArchiveHub's records about “{args.subject}”")
            return {"found": False, "note": "No matching person, place or organisation."}
        main = subjects[0]
        grouped = queries.claims_about(self.user, main.obj, args.predicate)
        questions = []
        disputed = []
        for predicate, claims in grouped.items():
            is_disputed = queries.is_disputed(claims)
            if is_disputed:
                disputed.append(predicate)
            questions.append(
                {
                    "question": predicate,
                    "sources_disagree": is_disputed,
                    "answers": [
                        {
                            "value": c.value,
                            "date": c.date_display or None,
                            "status": c.status,
                            "note": c.note or None,
                            "evidence": [
                                {
                                    "cite": self.cite_record(e.record),
                                    "record_id": str(e.record.id),
                                    "record": e.record.title,
                                    "what_it_says": e.note,
                                    "stance": e.stance,
                                    "suggested_weight": e.suggested_weight or None,
                                    "weight_suggested_by": e.weight_by or None,
                                }
                                for e in c.evidence.all()
                            ],
                        }
                        for c in claims
                    ],
                }
            )
        summary = f"Claims about {main.name} ({sum(len(c) for c in grouped.values())} found"
        summary += f"; sources disagree on {', '.join(disputed)})" if disputed else ")"
        self.log("Searched", summary)
        return {
            "found": True,
            "subject": main.name,
            "also_known_as": main.alt_names,
            "kind": main.kind,
            "questions": questions,
            "other_matches": [s.name for s in subjects[1:]],
            "missing_note": "Questions with no answers here are unknown, not settled.",
        }


def _record_brief(kit: ToolKit, r: SourceRecord) -> dict[str, Any]:
    return {
        "cite": kit.cite_record(r),
        "record_id": str(r.id),
        "title": r.title,
        "source": r.source.name,
        "date": r.date_display or None,
        "what_it_says": r.summary,
        "type": r.record_type,
        "url": r.url or None,
        "synthetic": r.is_synthetic,
    }


def _period(start: int | None, end: int | None) -> str:
    if start and end:
        return f"{start}–{end}"
    if start:
        return f"from {start}"
    if end:
        return f"to {end}"
    return ""


def _is_uuid(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F-]{32,36}", value))
