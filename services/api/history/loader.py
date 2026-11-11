"""Load the source directory and checked reference facts. Idempotent: safe to rerun."""

import json
from datetime import date
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from .models import (
    Assertion,
    AssertionEvidence,
    Method,
    Organisation,
    Place,
    Source,
    SourceRecord,
)

DATA = Path(__file__).parent / "data"
DATED = ("date_text", "year_from", "year_to", "date_precision")


def _read(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_sources() -> int:
    rows = _read("sources.json")
    for row in rows:
        row = dict(row)
        key = row.pop("key")
        if row.get("last_checked"):
            row["last_checked"] = date.fromisoformat(row["last_checked"])
        Source.objects.update_or_create(key=key, defaults=row)
    return len(rows)


def load_cheap_street() -> dict[str, int]:
    data = _read("cheap_street.json")
    checked_on = date.fromisoformat(data["checked_on"])

    places: dict[str, Place] = {}
    for row in data["places"]:
        parent = places.get(row.get("parent")) if row.get("parent") else None
        places[row["key"]], _ = Place.objects.update_or_create(
            key=row["key"],
            defaults={
                "name": row["name"],
                "kind": row.get("kind", "place"),
                "alt_names": row.get("alt_names", []),
                "parent": parent,
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "geocode_precision": row.get("geocode_precision", "unknown"),
                "geocode_source": row.get("geocode_source", ""),
                "note": row.get("note", ""),
            },
        )

    orgs: dict[str, Organisation] = {}
    for row in data["organisations"]:
        orgs[row["key"]], _ = Organisation.objects.update_or_create(
            key=row["key"],
            defaults={
                "name": row["name"],
                "kind": row.get("kind", "organisation"),
                "alt_names": row.get("alt_names", []),
                "place": places.get(row.get("place")),
            },
        )

    records: dict[str, SourceRecord] = {}
    for row in data["records"]:
        defaults = {
            "source": Source.objects.get(key=row["source"]),
            "title": row["title"],
            "url": row.get("url", ""),
            "record_type": row.get("record_type", ""),
            "summary": row.get("summary", ""),
            "place": places.get(row.get("place")),
            "fields": row.get("fields", {}),
            "checked_on": checked_on,
            "checked_note": "Checked against the live page",
        }
        defaults.update({k: row[k] for k in DATED if k in row})
        records[row["key"]], _ = SourceRecord.objects.update_or_create(
            key=row["key"], defaults=defaults
        )

    org_type = ContentType.objects.get_for_model(Organisation)
    evidence_count = 0
    for row in data["assertions"]:
        defaults = {
            "subject_type": org_type,
            "subject_id": orgs[row["subject"]].id,
            "predicate": row["predicate"],
            "value": row["value"],
            "status": row.get("status", "documented"),
            "method": Method.IMPORT,
            "note": row.get("note", ""),
        }
        defaults.update({k: row[k] for k in DATED if k in row})
        assertion, _ = Assertion.objects.update_or_create(key=row["key"], defaults=defaults)
        for record_key, stance, note, weight in row["evidence"]:
            AssertionEvidence.objects.update_or_create(
                assertion=assertion,
                record=records[record_key],
                defaults={
                    "stance": stance,
                    "note": note,
                    "suggested_weight": weight,
                    "weight_by": "editor",
                },
            )
            evidence_count += 1

    return {
        "places": len(places),
        "organisations": len(orgs),
        "records": len(records),
        "assertions": len(data["assertions"]),
        "evidence": evidence_count,
    }


@transaction.atomic
def load_all() -> dict[str, int]:
    counts = {"sources": load_sources()}
    counts.update(load_cheap_street())
    from genealogy.overlays import load_overlays

    counts["overlays"] = load_overlays()
    from culture.report import load_items

    counts["culture items"] = load_items()
    return counts
