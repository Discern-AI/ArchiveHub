"""Run one real search (and open one record) on every connector, and say what happened.

    python manage.py check_connectors
    python manage.py check_connectors --source trove --query "Newbury Berkshire"

Use it after adding a key to services/api/.env. It makes live requests to each outside
service, a few per source, within their published limits. Nothing is stored.
"""

from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from connectors.base import ConnectorError
from connectors.sources import CONNECTORS

# A query each source should have something for.
QUERIES = {
    "checked-reference": "Pigeons",
    "old-map-names": "Cheap Street",
    "wikidata": "Newbury",
    "europeana": "Newbury Berkshire",
    "tna-discovery": "Cheap Street Newbury",
    "geograph": "SU4767",
    "os-names": "Cheap Street Newbury",
    "digitalnz": "Newbury Berkshire",
    "trove": "Newbury Berkshire",
    "dpla": "Newbury Berkshire",
    "historic-england": "Cheap Street Newbury",
    "the-gazette": "Newbury",
    "geonames": "Newbury",
    "met-museum": "Newbury",
    "art-institute-chicago": "Newbury",
    "openalex": "Newbury Berkshire history",
}


class Command(BaseCommand):
    help = "Run a live search on every connector and report what works."

    def add_arguments(self, parser):
        parser.add_argument("--source", action="append", help="Only this connector (repeatable)")
        parser.add_argument("--query", help="Search for this instead of the default")

    def handle(self, *args, source=None, query=None, **options):
        keys = source or list(CONNECTORS)
        unknown = [k for k in keys if k not in CONNECTORS]
        if unknown:
            self.stderr.write(f"Unknown source(s): {', '.join(unknown)}")
            return
        counts = {"works": 0, "not set up": 0, "no results": 0, "failed": 0}
        for key in keys:
            status, detail = self.check_one(CONNECTORS[key], query or QUERIES.get(key, "Newbury"))
            counts[status] += 1
            style = {
                "works": self.style.SUCCESS,
                "not set up": self.style.WARNING,
                "no results": self.style.WARNING,
                "failed": self.style.ERROR,
            }[status]
            self.stdout.write(f"{style(status.upper().ljust(10))} {key:<22} {detail}")
        self.stdout.write(
            "\n" + ", ".join(f"{n} {label}" for label, n in counts.items() if n) + "."
        )

    def check_one(self, connector, query: str) -> tuple[str, str]:
        if hasattr(connector, "configured") and not connector.configured():
            return "not set up", connector.setup_note
        started = time.monotonic()
        try:
            page = connector.search(query, page_size=3)
            if not page.records:
                return "no results", f"no results for “{query}”"
            first = page.records[0]
            record = connector.get_record(first.id)
        except ConnectorError as exc:
            return "failed", f"{exc.user_message} ({exc.kind}: {str(exc)[:120]})"
        seconds = time.monotonic() - started
        more = ", more pages" if page.next_cursor else ""
        return (
            "works",
            f"{len(page.records)} results{more}, e.g. “{record.title[:60]}” ({seconds:.1f}s)",
        )
