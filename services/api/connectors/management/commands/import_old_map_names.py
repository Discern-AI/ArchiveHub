"""Import old OS map names from the GB1900 raw data dump (CC0) into a hosted dataset.

python manage.py import_old_map_names --zip var/downloads/gb1900/GB1900_final_raw_dump_july_2018.zip
python manage.py import_old_map_names --zip ... --all          # the whole of Great Britain
python manage.py import_old_map_names --zip ... --bbox 51.3,-1.7,51.6,-0.9
"""

import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from connectors.gb1900 import WEST_BERKSHIRE, best_reading, read_pins, sha256
from connectors.models import Dataset, DatasetRow
from connectors.sources import OldMapNamesConnector
from history.models import Source

BATCH = 5000


class Command(BaseCommand):
    help = "Import names from the OS six-inch maps (GB1900 raw data dump, CC0)."

    def add_arguments(self, parser):
        parser.add_argument("--zip", required=True, help="Path to the GB1900 raw dump zip")
        scope = parser.add_mutually_exclusive_group()
        scope.add_argument("--all", action="store_true", help="Import all of Great Britain")
        scope.add_argument("--bbox", help="min_lat,min_lon,max_lat,max_lon")

    def handle(self, *args, **opts):
        path = Path(opts["zip"])
        if not path.exists():
            raise CommandError(f"No file at {path}")
        source = Source.objects.filter(key="gb1900").first()
        if source is None:
            raise CommandError(
                "Run load_reference_data first (the directory needs the GB1900 entry)."
            )

        if opts["all"]:
            box, scope = None, "Great Britain"
        elif opts["bbox"]:
            try:
                box = tuple(float(v) for v in opts["bbox"].split(","))
                assert len(box) == 4
            except (ValueError, AssertionError) as exc:
                raise CommandError(
                    "--bbox needs four numbers: min_lat,min_lon,max_lat,max_lon"
                ) from exc
            scope = f"area {opts['bbox']}"
        else:
            box, scope = WEST_BERKSHIRE, "Newbury and West Berkshire"

        self.stdout.write(f"Checking {path.name}…")
        digest = sha256(path)
        self.stdout.write(f"  sha256 {digest}")
        with zipfile.ZipFile(path) as zf:
            self.stdout.write(f"Reading pins for {scope}…")
            pins = read_pins(zf, box, progress=self.stdout.write)

        connector = OldMapNamesConnector()
        with transaction.atomic():
            dataset, _ = Dataset.objects.update_or_create(
                key=connector.dataset_key,
                defaults={
                    "name": connector.name,
                    "source": source,
                    "description": connector.description,
                    "licence": "CC0 1.0",
                    "citation": "GB1900 final raw gazetteer data dump, made available by the "
                    "GB1900 Project (www.visionofbritain.org.uk)",
                    "original_file": path.name,
                    "original_sha256": digest,
                    "import_scope": scope,
                },
            )
            DatasetRow.objects.filter(dataset=dataset).delete()
            batch = []
            for pin_id, pin in pins.items():
                title, variants, total = best_reading(pin)
                if not title:
                    continue
                batch.append(
                    DatasetRow(
                        dataset=dataset,
                        external_id=pin_id,
                        title=title[:400],
                        title_lower=title[:400].lower(),
                        latitude=round(pin.lat, 6),
                        longitude=round(pin.lon, 6),
                        fields={"variants": variants, "transcriptions": total},
                    )
                )
                if len(batch) >= BATCH:
                    DatasetRow.objects.bulk_create(batch)
                    batch = []
            DatasetRow.objects.bulk_create(batch)
            dataset.row_count = DatasetRow.objects.filter(dataset=dataset).count()
            dataset.imported_at = timezone.now()
            dataset.save()

        self.stdout.write(
            self.style.SUCCESS(f"Imported {dataset.row_count:,} map labels for {scope}.")
        )
