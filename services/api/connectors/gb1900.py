"""Reading the GB1900 final raw data dump (CC0). Streams from the zip; never extracts it.

The archive's CSVs are UTF-16. Locations carry coordinates as hex EWKB points; each pin
has several volunteer transcriptions, of which we keep the most agreed reading and the
variants. Contributor IDs are not kept.
"""

from __future__ import annotations

import csv
import hashlib
import io
import struct
import sys
import zipfile
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

BASE = "GB1900_final_raw_dump_july_2018/"
# Roughly Newbury and West Berkshire: (min_lat, min_lon, max_lat, max_lon)
WEST_BERKSHIRE = (51.33, -1.60, 51.56, -1.00)

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def parse_ewkb_point(hex_text: str) -> tuple[float, float] | None:
    """Return (lat, lon) from a hex (E)WKB point, or None if it isn't one."""
    try:
        raw = bytes.fromhex(hex_text.strip())
    except ValueError:
        return None
    if len(raw) < 21:
        return None
    order = "<" if raw[0] == 1 else ">"
    (geom_type,) = struct.unpack(order + "I", raw[1:5])
    offset = 5
    if geom_type & 0x20000000:  # SRID present
        offset += 4
    if geom_type & 0xFF != 1:  # not a point
        return None
    x, y = struct.unpack(order + "dd", raw[offset : offset + 16])
    return y, x


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(zf: zipfile.ZipFile, name: str) -> Iterator[dict[str, str]]:
    with zf.open(BASE + name) as raw:
        yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-16", newline=""))


@dataclass
class Pin:
    lat: float
    lon: float
    first: str
    readings: Counter = field(default_factory=Counter)


def in_box(lat: float, lon: float, box: tuple[float, float, float, float] | None) -> bool:
    if box is None:
        return True
    min_lat, min_lon, max_lat, max_lon = box
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def read_pins(
    zf: zipfile.ZipFile, box: tuple[float, float, float, float] | None, progress=None
) -> dict[str, Pin]:
    pins: dict[str, Pin] = {}
    for n, row in enumerate(rows(zf, "gb1900_locations.csv"), 1):
        point = parse_ewkb_point(row.get("g_point_wgs", ""))
        if point and in_box(*point, box):
            pins[row["pin_id"]] = Pin(
                point[0], point[1], (row.get("first_transcription") or "").strip()
            )
        if progress and n % 500_000 == 0:
            progress(f"  locations read: {n:,} (kept {len(pins):,})")
    for n, row in enumerate(rows(zf, "gb1900_transcriptions.csv"), 1):
        pin = pins.get(row.get("pin_id", ""))
        text = (row.get("transcription") or "").strip()
        if pin and text:
            pin.readings[text] += 1
        if progress and n % 1_000_000 == 0:
            progress(f"  transcriptions read: {n:,}")
    return pins


def best_reading(pin: Pin) -> tuple[str, list[str], int]:
    """Most agreed reading (ties go to the first transcription), other readings, total."""
    if not pin.readings:
        return pin.first, [], 0
    top = max(pin.readings.values())
    leaders = [t for t, c in pin.readings.items() if c == top]
    title = pin.first if pin.first in leaders else sorted(leaders)[0]
    variants = [t for t, _ in pin.readings.most_common() if t != title][:5]
    return title, variants, sum(pin.readings.values())
