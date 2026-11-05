"""A small GEDCOM reader and date parser (5.5.1 and 7.0 line format).

Written here rather than using a GPL library (ADR-010). It reads the parts ArchiveHub
uses (people, families, names, sex, life events with dates and places) and keeps the
original date text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

LINE = re.compile(r"^\s*(\d+)\s+(?:(@[^@]+@)\s+)?(\w+)(?:\s(.*))?$")
MONTH_NAMES = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
MONTHS = {m: i for i, m in enumerate(MONTH_NAMES, 1)}
YEAR = re.compile(r"\b(\d{3,4})\b")


@dataclass
class Node:
    level: int
    tag: str
    value: str = ""
    xref: str | None = None
    children: list[Node] = field(default_factory=list)

    def first(self, tag: str) -> Node | None:
        return next((c for c in self.children if c.tag == tag), None)

    def all(self, tag: str) -> list[Node]:
        return [c for c in self.children if c.tag == tag]

    def text(self, tag: str) -> str:
        node = self.first(tag)
        return node.value.strip() if node else ""


def parse(text: str) -> list[Node]:
    """Parse GEDCOM text into top-level records. Malformed lines are skipped."""
    roots: list[Node] = []
    stack: list[Node] = []
    for raw in text.splitlines():
        m = LINE.match(raw.lstrip("﻿"))
        if not m:
            continue
        level, xref, tag, value = int(m[1]), m[2], m[3].upper(), m[4] or ""
        if tag in ("CONC", "CONT") and stack:
            parent = stack[-1] if stack[-1].level == level - 1 else None
            if parent is not None:
                parent.value += ("\n" if tag == "CONT" else "") + value
                continue
        node = Node(level, tag, value, xref)
        while stack and stack[-1].level >= level:
            stack.pop()
        if stack:
            stack[-1].children.append(node)
        elif level == 0:
            roots.append(node)
        else:
            continue
        stack.append(node)
    return roots


def clean_name(value: str) -> str:
    """'John /Smith/' -> 'John Smith'."""
    return re.sub(r"\s+", " ", value.replace("/", " ")).strip()


@dataclass
class GDate:
    text: str
    year_from: int | None
    year_to: int | None
    precision: str


def parse_date(text: str) -> GDate:
    t = text.strip()
    up = t.upper()
    years = [int(y) for y in YEAR.findall(up)]
    if not years:
        return GDate(t, None, None, "unknown")
    if up.startswith(("BET", "FROM")) and len(years) >= 2:
        return GDate(t, years[0], years[1], "range")
    if up.startswith(("ABT", "CAL", "EST", "ABOUT")):
        return GDate(t, years[0], years[0], "approximate")
    if up.startswith("BEF"):
        return GDate(t, None, years[0], "before")
    if up.startswith("AFT"):
        return GDate(t, years[0], None, "after")
    parts = up.split()
    exact = len(parts) == 3 and parts[1][:3] in MONTHS
    return GDate(t, years[0], years[0], "exact" if exact else "year")


EVENTS = {
    "BIRT": "birth",
    "CHR": "baptism",
    "BAPM": "baptism",
    "DEAT": "death",
    "BURI": "burial",
    "MARR": "marriage",
}
