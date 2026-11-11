"""Refresh the Life and times data from its publishers (both Open Government Licence).

python manage.py refresh_context_data

A download that doesn't look right is refused and the existing file is kept.
"""

import urllib.request

from django.core.management.base import BaseCommand, CommandError

from connectors.sources import _TLS
from genealogy import context

SOURCES = [
    (
        context.RPI_FILE,
        "https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/"
        "timeseries/cdko/mm23",
        '"CDID","CDKO"',
    ),
    (
        context.CET_FILE,
        "https://www.metoffice.gov.uk/hadobs/hadcet/data/meantemp_monthly_totals.txt",
        "Mean Central England Temperature",
    ),
]


class Command(BaseCommand):
    help = "Download fresh copies of the price index and Central England temperatures."

    def handle(self, *args, **opts):
        for path, url, marker in SOURCES:
            # Fixed https addresses above, never user input.
            req = urllib.request.Request(  # noqa: S310
                url, headers={"User-Agent": "ArchiveHub data refresh"}
            )
            try:
                with urllib.request.urlopen(req, timeout=60, context=_TLS) as resp:  # noqa: S310
                    body = resp.read().decode("utf-8-sig")
            except OSError as exc:
                raise CommandError(f"Couldn't download {url}: {exc}") from exc
            if marker not in body or len(body.splitlines()) < 200:
                raise CommandError(f"{url} didn't look right; {path.name} was kept as it was.")
            path.write_text(body, encoding="utf-8")
            self.stdout.write(f"Updated {path.name}")
        context.rpi.cache_clear()
        context.cet.cache_clear()
        self.stdout.write(self.style.SUCCESS("Life and times data refreshed."))
