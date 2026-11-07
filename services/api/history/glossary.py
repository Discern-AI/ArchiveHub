"""Explanations of old terms (money, Poor Law) and Ordnance Survey map abbreviations.

Every entry is in our own words and points to the page it was checked against
(history/data/glossary.json). An explanation is context, never evidence about a person.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data" / "glossary.json"
NLS_LIST = "https://maps.nls.uk/os/abbrev/"
NLS_CREDIT = (
    "Ordnance Survey abbreviations, National Library of Scotland (compiled by Dr Richard Oliver)"
)


@cache
def _data() -> dict[str, Any]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _norm(text: str) -> str:
    return re.sub(r"[.\s]", "", text)


def abbreviation(text: str) -> dict[str, Any] | None:
    """Possible meanings of an OS map abbreviation such as 'P.H.' or 'S.Ps'.

    Case matters (CH and Ch differ). A plural like 'SPs' falls back to 'SP'.
    """
    key = _norm(text)
    if not key or len(key) > 6:
        return None
    entries = {e["abbr"]: e for e in _data()["abbreviations"]}
    entry = entries.get(key)
    plural = False
    if entry is None and key.endswith("s") and key[:-1] in entries:
        entry, plural = entries[key[:-1]], True
    if entry is None:
        return None
    meanings = entry["meanings"]
    return {
        "abbr": text.strip(),
        "meanings": meanings,
        "plural": plural,
        "text": (
            ("could be: " if len(meanings) > 1 else "")
            + ", ".join(meanings)
            + (" (plural)" if plural else "")
        ),
        "source_url": entry["source_url"],
        "source": NLS_CREDIT,
    }


def terms() -> list[dict[str, Any]]:
    return _data()["terms"]


WORD = re.compile(r"[a-z0-9£/']+")
STOP = {"the", "and", "what", "was", "who", "how", "does", "did", "for", "old", "mean", "means"}


def search_terms(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Terms whose name or other names match the query (whole words or phrases)."""
    q = query.lower().strip()
    if not q:
        return []
    words = {w for w in WORD.findall(q) if len(w) > 2 and w not in STOP}
    scored = []
    for t in terms():
        names = [t["term"].lower(), t["key"].replace("-", " "), *[a.lower() for a in t["also"]]]
        score = 0
        for name in names:
            plain = re.sub(r"\s*\(.*?\)", "", name).strip()
            if plain and (plain == q or f" {plain} " in f" {q} "):
                # A longer exact phrase is a better match ("settlement examination").
                score = max(score, 3 + len(plain) / 100)
            elif set(WORD.findall(plain)) & words and len(plain) > 2:
                score = max(score, 1)
        if score:
            scored.append((score, t))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["term"]))
    return [t for _, t in scored[:limit]]
