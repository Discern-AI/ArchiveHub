"""Built-in Lifeline overlays (wars, laws, records), loaded from checked data."""

import json
from datetime import date
from pathlib import Path

from .models import OverlayEvent

DATA = Path(__file__).parent / "data" / "overlays.json"


def load_overlays() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    checked = date.fromisoformat(data["checked_on"])
    keys = []
    for row in data["overlays"]:
        row = dict(row)
        key = row.pop("key")
        keys.append(key)
        OverlayEvent.objects.update_or_create(
            project=None, key=key, defaults={**row, "checked_on": checked}
        )
    # Built-ins removed from the file are removed here too; users' markers are untouched.
    OverlayEvent.objects.filter(project=None).exclude(key__in=keys).delete()
    return len(keys)
