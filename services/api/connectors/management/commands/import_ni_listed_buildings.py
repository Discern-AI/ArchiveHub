"""Import Northern Ireland's listed buildings (Open Data NI, OGL) into a hosted dataset.

python manage.py import_ni_listed_buildings --file var/downloads/ni/hb_05112026.geojson

The file is the "Listed Buildings Northern Ireland" GeoJSON from Open Data NI
(Department for Communities, Historic Environment Division), published monthly. It's
in Irish Grid coordinates. Only listed grades are imported; "Record Only" and delisted
entries aren't listed buildings, so they're left out.
"""

import hashlib
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from connectors.live import irish_grid_to_wgs84
from connectors.models import Dataset, DatasetRow
from history.models import Source

DATASET_KEY = "ni-listed-buildings"
LISTED_GRADES = {"A", "B+", "B1", "B2", "B"}
BATCH = 5000


def _lines(value) -> list[str]:
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


def row_from_feature(feature: dict) -> dict | None:
    """What we keep of one building, or None if it isn't listed or has no position."""
    p = feature.get("properties") or {}
    coords = (feature.get("geometry") or {}).get("coordinates") or []
    grade = str(p.get("CurrentGra") or "").strip()
    ref = str(p.get("HB_ref") or "").strip()
    if grade not in LISTED_GRADES or not ref or len(coords) != 2:
        return None
    lat, lng = irish_grid_to_wgs84(float(coords[0]), float(coords[1]))
    address = _lines(p.get("Address"))
    return {
        "external_id": ref[:64],
        "title": (address[0] if address else ref)[:400],
        "latitude": round(lat, 6),
        "longitude": round(lng, 6),
        "fields": {
            "grade": grade,
            "address": ", ".join(address),
            "built": str(p.get("Date_Const") or "").strip(),
            "extent": str(p.get("Extent") or "").strip(),
            "townland": ", ".join(_lines(p.get("Townland"))),
            "council": str(p.get("Council") or "").strip(),
            "current_use": str(p.get("CurrentUse") or "").strip(),
        },
    }


class Command(BaseCommand):
    help = "Import Northern Ireland's listed buildings (Open Data NI GeoJSON, OGL)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to the GeoJSON file")

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(f"No file at {path}")
        source = Source.objects.filter(key="ni-historic-buildings").first()
        if source is None:
            raise CommandError("Run load_reference_data first (the directory needs this entry).")
        raw = path.read_bytes()
        try:
            data = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CommandError("That file isn't GeoJSON.") from exc
        crs = ((data.get("crs") or {}).get("properties") or {}).get("name", "")
        if "29902" not in crs and "29900" not in crs:
            raise CommandError(f"Expected Irish Grid coordinates (EPSG:29902), found {crs!r}.")

        rows, seen = [], set()
        for feature in data.get("features") or []:
            row = row_from_feature(feature)
            if row and row["external_id"] not in seen:
                seen.add(row["external_id"])
                rows.append(row)

        with transaction.atomic():
            dataset, _ = Dataset.objects.update_or_create(
                key=DATASET_KEY,
                defaults={
                    "name": "Listed buildings in Northern Ireland",
                    "source": source,
                    "description": "Listed buildings from the Historic Buildings Record, with "
                    "grade, address and the date range they were built in.",
                    "licence": "Open Government Licence",
                    "citation": "Listed Buildings Northern Ireland, Department for Communities "
                    "Historic Environment Division, via Open Data NI. Open Government Licence.",
                    "original_file": path.name,
                    "original_sha256": hashlib.sha256(raw).hexdigest(),
                    "import_scope": "Northern Ireland",
                },
            )
            DatasetRow.objects.filter(dataset=dataset).delete()
            batch = []
            for row in rows:
                batch.append(DatasetRow(dataset=dataset, title_lower=row["title"].lower(), **row))
                if len(batch) >= BATCH:
                    DatasetRow.objects.bulk_create(batch)
                    batch = []
            DatasetRow.objects.bulk_create(batch)
            dataset.row_count = len(rows)
            dataset.imported_at = timezone.now()
            dataset.save()
        self.stdout.write(
            self.style.SUCCESS(f"Imported {len(rows):,} listed buildings in Northern Ireland.")
        )
