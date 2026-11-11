"""Explain this record: four layers, kept apart.

1. What it says: the record's own wording, unchanged.
2. What the words mean: checked explanations of the terms, institutions and record types
   it uses, for the right period and place. A term from before an institution existed is
   explained as it was then (a 1790 "workhouse" was a parish one, not a union one).
3. What it may mean for them: careful, general readings, labelled as interpretation:
   "people went into workhouses for many reasons", never "your family did".
4. Where to find out more: records to look for, where they're kept, and what to ask.

Only checked entries (the glossary) and reviewed contributions (with credit) are used.
"""

from __future__ import annotations

import re
from typing import Any

from history.glossary import terms

from .models import Explanation, ExplanationStatus
from .record_guide import record_office_for

SENSITIVE = {"workhouse", "pauper", "admitted-discharged", "quarter-sessions-settlement"}


def _names(entry: dict[str, Any]) -> list[str]:
    plain = re.sub(r"\s*\(.*?\)", "", entry["term"]).strip()
    return [n for n in {plain, *entry.get("also", [])} if n and len(n) > 2]


def _found(text: str, names: list[str]) -> str | None:
    low = f" {' '.join(text.lower().split())} "
    for n in sorted(names, key=len, reverse=True):
        if re.search(rf"(?<![a-z]){re.escape(n.lower())}(?![a-z])", low):
            return n
    return None


def _period_note(entry: dict[str, Any], year: int | None) -> tuple[bool, str]:
    """(applies, note) for the record's year against the explanation's period."""
    start, end = entry.get("period_from"), entry.get("period_to")
    if year is None or (start is None and end is None):
        return True, ""
    if start is not None and year < start:
        return False, entry.get("before") or (
            f"This explanation is for {start} onwards; this record is from {year}, "
            "so it may not apply as written."
        )
    if end is not None and year > end:
        return False, f"This explanation is for up to {end}; this record is from {year}."
    return True, ""


def explain_record(text: str, year: int | None = None, place: str = "") -> dict[str, Any]:
    text = text.strip()
    words, may_mean, more = [], [], []
    seen_more: set[str] = set()
    sensitive = False
    entries = [dict(e, contributed=False) for e in terms()]
    for c in Explanation.objects.filter(status=ExplanationStatus.REVIEWED):
        entries.append({
            "key": f"contributed-{c.id}", "term": c.term, "also": c.also, "meaning": c.meaning,
            "may_mean": c.may_mean, "area": c.area, "period_from": c.period_from,
            "period_to": c.period_to, "sources": c.sources, "contributed": True,
            "credit": c.credit,
            "where_to_look": [{"text": c.where_to_look, "sources": c.sources}]
            if c.where_to_look else [],
        })  # fmt: skip
    for e in entries:
        hit = _found(text, _names(e))
        if not hit:
            continue
        applies, note = _period_note(e, year)
        sensitive = sensitive or e["key"] in SENSITIVE
        words.append({
            "term": e["term"],
            "found": hit,
            "meaning": e["meaning"],
            "area": e.get("area", ""),
            "applies": applies,
            "period_note": note,
            "sources": e.get("sources", []),
            "contributed_by": e.get("credit", "") if e.get("contributed") else "",
        })  # fmt: skip
        if e.get("may_mean") and applies:
            may_mean.append({"term": e["term"], "text": e["may_mean"],
                             "sources": e.get("sources", [])})  # fmt: skip
        for w in e.get("where_to_look", []) if applies else []:
            if w["text"] not in seen_more:
                seen_more.add(w["text"])
                more.append({"text": w["text"], "sources": w.get("sources", [])})
        if not applies and e.get("before"):
            # Before the institution existed: point at the earlier records instead.
            for w in next((x for x in terms() if x["key"] == "pauper"), {}).get(
                "where_to_look", []
            ):
                if w["text"] not in seen_more:
                    seen_more.add(w["text"])
                    more.append({"text": w["text"], "sources": w.get("sources", [])})
    if place.strip():
        office = record_office_for(place)
        more.append({"text": f"For {place.strip()}, start with {office}. Ask what survives for "
                     "the records above, for the years you need.", "sources": []})  # fmt: skip
    return {
        "says": {"text": text, "year": year, "place": place.strip()},
        "words": words,
        "may_mean": may_mean,
        "may_mean_label": "Careful readings of what records like this usually show. They "
        "describe what was common, not what happened to this person.",
        "find_out_more": more,
        "sensitive": sensitive,
        "sensitive_note": "Records of workhouses and poor relief can be hard to read about. "
        "Descendants decide what's shared; nothing here is published."
        if sensitive
        else "",
        "nothing_found": not words,
        "note": "Only checked explanations are used. If a word isn't explained, ask the "
        "assistant, or offer an explanation for others."
        if not words
        else "",
    }
