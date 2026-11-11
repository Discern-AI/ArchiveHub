"""Life and times: what the world around a person was like in a given year.

Everything here is context, never a fact about the person:
- Money: how prices then compare with now, from the ONS long-run Retail Prices Index
  (CDKO, from 1800). A price index comparison, not what any one thing cost.
- Weather: the Met Office Central England Temperature series (from 1659), for a region of
  England, not anyone's town.
- What was happening: wars, laws and census nights, from the Lifeline's checked overlays.
- Contemporary accounts: pointers only. Diaries and oral histories need permission to show.

Both data files are Open Government Licence and kept in genealogy/data; refresh them with
`python manage.py refresh_context_data`.
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.db.models import Q

from .models import OverlayEvent

DATA = Path(__file__).parent / "data"
RPI_FILE = DATA / "ons_cdko.csv"
CET_FILE = DATA / "hadcet_monthly.txt"
RPI_CREDIT = (
    "Office for National Statistics, Retail Prices Index: long run series (CDKO). "
    "Contains public sector information licensed under the Open Government Licence v3.0."
)
RPI_URL = "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/cdko/mm23"
CET_CREDIT = (
    "Met Office Hadley Centre, Central England Temperature (HadCET). © Crown Copyright, "
    "Open Government Licence."
)
CET_URL = "https://www.metoffice.gov.uk/hadobs/hadcet/"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]  # fmt: skip
NORMAL = (1961, 1990)  # the long-standing climate comparison period


@lru_cache
def rpi() -> dict[int, float]:
    """Annual index values only (the file also has months and quarters)."""
    out = {}
    with RPI_FILE.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.reader(fh):
            if len(row) == 2 and re.fullmatch(r"\d{4}", row[0]):
                try:
                    out[int(row[0])] = float(row[1])
                except ValueError:
                    continue
    return out


@lru_cache
def cet() -> dict[int, list[float | None]]:
    """{year: [12 monthly means, annual mean]}; -99.9 marks a month not yet measured."""
    out = {}
    for line in CET_FILE.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 14 and parts[0].isdigit():
            values = [float(v) for v in parts[1:]]
            out[int(parts[0])] = [None if v <= -99 else v for v in values]
    return out


def money(year: int) -> dict[str, Any]:
    series = rpi()
    if not series:
        return {"available": False, "note": "Price data isn't loaded."}
    latest = max(series)
    if year not in series:
        first = min(series)
        return {
            "available": False,
            "note": f"The long-run price index starts in {first}." if year < first else
            f"There's no price index for {year} yet.",
        }  # fmt: skip
    ratio = series[latest] / series[year]
    return {
        "available": True,
        "year": year,
        "latest_year": latest,
        "multiplier": round(ratio, 1),
        "sentence": f"Prices in {latest} were about {ratio:,.0f} times those in {year}: "
        f"£1 in {year} would buy roughly what £{ratio:,.0f} did in {latest}."
        if ratio >= 2
        else f"Prices in {latest} were about {ratio:.1f} times those in {year}.",
        "note": "A comparison of average retail prices, not of wages or of what any one "
        "thing cost. Wages and particular prices changed by different amounts.",
        "source": RPI_CREDIT,
        "source_url": RPI_URL,
    }


def weather(year: int) -> dict[str, Any]:
    series = cet()
    row = series.get(year)
    if not row or row[12] is None:
        first = min(series) if series else 1659
        return {
            "available": False,
            "note": f"The Central England temperature record starts in {first}."
            if year < first
            else f"The year {year} isn't complete in the record yet.",
        }
    normal_years = [series[y][12] for y in range(NORMAL[0], NORMAL[1] + 1) if y in series]
    normal = sum(normal_years) / len(normal_years)
    months = row[:12]
    cold = min(range(12), key=lambda m: months[m])
    warm = max(range(12), key=lambda m: months[m])
    diff = row[12] - normal
    ordered = sorted(v[12] for v in series.values() if v[12] is not None)
    total = len(ordered)
    colder = ordered.index(row[12]) + 1
    warmer = total - colder + 1
    since = min(series)
    # Only worth saying when it stands out.
    if colder <= 30:
        rank = (
            f"One of the coldest years on record: {_ordinal(colder)} coldest of {total} "
            f"since {since}."
        )
    elif warmer <= 30:
        rank = (
            f"One of the warmest years on record: {_ordinal(warmer)} warmest of {total} "
            f"since {since}."
        )
    else:
        rank = ""
    if abs(diff) < 0.3:
        compare = "about average"
    else:
        word = "warmer" if diff > 0 else "colder"
        compare = f"{abs(diff):.1f}°C {word} than the 1961–1990 average"
    return {
        "available": True,
        "year": year,
        "annual_mean": row[12],
        "sentence": f"In central England, {year} averaged {row[12]:.1f}°C, {compare}. "
        f"The coldest month was {MONTHS[cold]} ({months[cold]:.1f}°C) and the warmest "
        f"{MONTHS[warm]} ({months[warm]:.1f}°C).",
        "rank": rank,
        "note": "The record covers a roughly triangular area of England enclosed by "
        "Lancashire, London and Bristol. It isn't their town's weather, and it can't say "
        "what any one day was like.",
        "source": CET_CREDIT,
        "source_url": CET_URL,
    }


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def happening(year: int, project=None) -> list[dict[str, Any]]:
    q = Q(project=None)
    if project is not None:
        q |= Q(project=project)
    out = []
    for o in OverlayEvent.objects.filter(q).filter(year_from__lte=year):
        if (o.year_to or o.year_from) < year and o.kind != "law":
            continue
        if o.kind == "law" and year - o.year_from > 0:
            label = f"in force since {o.year_from}"
        elif o.year_to:
            label = "under way"
        else:
            label = "this year"
        if o.kind == "records" and o.year_from != year:
            continue
        out.append(
            {
                "title": o.title,
                "date_text": o.date_text,
                "area": o.area,
                "kind": o.kind,
                "when": label,
                "source_title": o.source_title,
                "source_url": o.source_url,
            }
        )
    return out


def life_and_times(year: int, project=None) -> dict[str, Any]:
    return {
        "year": year,
        "money": money(year),
        "weather": weather(year),
        "happening": happening(year, project),
        "accounts": {
            "available": False,
            "note": "Diaries, letters and oral histories describing life then need the "
            "holders' permission to show here. The source directory lists where to find them.",
            "search": "diaries",
        },
        "label": "Context: what the world was like, not a fact about anyone in particular.",
    }
