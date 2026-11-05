"""Grading for assistant answers. Pure functions: deterministic, no model calls."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

UNKNOWN = re.compile(
    r"couldn['’]t find|could not find|can['’]t find|no record"
    r"|not (?:been )?(?:found|recorded|known)|don['’]t know|do not know|unknown"
    r"|isn['’]t recorded|no (?:date|information|evidence)"
    r"|doesn['’]t say|does not say|not say when|don['’]t have",
    re.I,
)
DISPUTE = re.compile(
    r"disagree|differ|conflict|disput|two (?:different )?address|inconsisten", re.I
)
NEXT_STEPS = re.compile(r"next|try|check|contact|visit|ask|look (?:at|for|in)", re.I)
URL = re.compile(r"https?://\S+")
CITE = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]")


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


def cited_numbers(text: str) -> list[int]:
    return [int(n) for group in CITE.findall(text) for n in re.findall(r"\d+", group)]


def grade(
    case: dict[str, Any],
    answer: str,
    valid_numbers: set[int],
    cited_record_keys: set[str],
    source_urls: set[str],
) -> list[Check]:
    """Grade one answer. `valid_numbers` are the citation numbers tools actually returned."""
    checks: list[Check] = []

    bad = sorted({n for n in cited_numbers(answer) if n not in valid_numbers})
    checks.append(Check("no invented citations", not bad, f"unknown numbers: {bad}" if bad else ""))

    stray = [u for u in URL.findall(answer) if u.rstrip(".,);]") not in source_urls]
    checks.append(Check("no invented links", not stray, ", ".join(stray)))

    for phrase in case.get("must_mention", []):
        checks.append(Check(f"mentions “{phrase}”", phrase.lower() in answer.lower()))

    for pattern in case.get("must_not_match", []):
        hit = re.search(pattern, answer, re.I)
        checks.append(Check(f"avoids /{pattern}/", not hit, hit.group(0) if hit else ""))

    if case.get("must_match_any"):
        ok = any(p.lower() in answer.lower() for p in case["must_match_any"])
        checks.append(Check("signals uncertainty", ok))

    if case.get("must_admit_unknown"):
        checks.append(Check("says what isn't known", bool(UNKNOWN.search(answer))))

    if case.get("must_flag_dispute"):
        checks.append(Check("flags that sources disagree", bool(DISPUTE.search(answer))))

    if case.get("must_suggest_next_steps"):
        checks.append(Check("suggests next steps", bool(NEXT_STEPS.search(answer))))

    for key in case.get("must_cite_records", []):
        checks.append(Check(f"cites {key}", key in cited_record_keys))

    return checks
