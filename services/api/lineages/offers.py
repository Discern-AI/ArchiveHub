"""Records that can be ordered, and how. Each offer is from the holder's own pages, with
its price and delivery time as published and the date that was checked.

To start with every offer is a referral: the person orders from the holder (ArchiveHub
doesn't take payment or resell), and ArchiveHub keeps track and files the record when
it arrives. Other routes (ordering for the user, partners, local researchers) need the
holder's permission and a payment provider first.
"""

from __future__ import annotations

from datetime import date
from typing import Any

GRO_FAQ = "https://www.gro.gov.uk/gro/content/certificates/faq.asp"
GOV_UK = "https://www.gov.uk/order-copy-birth-death-marriage-certificate"
CHECKED = "2026-11-11"
GRO_RIGHTS = (
    "A copy of a public record for your own research. Ask the General Register Office "
    "before publishing the image."
)
OUTSIDE_GRO = ("scotland", "ireland", "isle of man", "jersey", "guernsey")


def _gro(key, title, event_types, fees, delivery, should_show, needs_ref, years=None):
    return {
        "key": key,
        "title": title,
        "holder": "General Register Office (England and Wales)",
        "events": event_types,
        "route": "referral",
        "fees": fees,
        "delivery": delivery,
        "should_show": should_show,
        "needs_index_reference": needs_ref,
        "years": years or {},
        "url": "https://www.gro.gov.uk/gro/content/certificates/",
        "how": "Order on the General Register Office website, then mark it ordered here. When "
        "it arrives, upload it to your Archive and mark it received.",
        "rights_label": GRO_RIGHTS,
        "sources": [
            {"title": "GRO certificate FAQ (prices and delivery)", "url": GRO_FAQ},
            {
                "title": "GOV.UK: Order a copy of a birth, death or marriage certificate",
                "url": GOV_UK,
            },
        ],  # fmt: skip
        "checked_on": CHECKED,
    }


def offers() -> list[dict[str, Any]]:
    hundred_years_ago = date.today().year - 100
    return [
        _gro(
            "gro-certificate",
            "Certificate (paper)",
            ["birth", "marriage", "death"],
            [{"label": "General Register Office fee", "pence": 1250}],
            "Sent on the fourth working day with a GRO index reference; the fifteenth "
            "working day without one (and £3.50 more for them to find it).",
            "A certified copy of the full registration entry.",
            False,
        ),
        _gro(
            "gro-pdf",
            "PDF copy",
            ["birth", "death"],
            [{"label": "General Register Office fee", "pence": 800}],
            "In your GRO online account within four working days (ordered before 4pm).",
            "An image of the registration entry, as a PDF.",
            True,
            {"birth": (1837, hundred_years_ago), "death": (1837, 1957)},
        ),
        _gro(
            "gro-online-view",
            "Online view of the register image",
            ["birth", "death"],
            [{"label": "General Register Office fee", "pence": 300}],
            "In your GRO online account once the order is complete.",
            "A digital image of the registration entry to view online.",
            True,
            {"birth": (1837, hundred_years_ago), "death": (1837, 1957)},
        ),
    ]


def offers_for(event: str, year: int | None, place: str = "") -> dict[str, Any]:
    """What could be ordered for one event, and why anything isn't offered."""
    low = place.lower()
    if any(w in low for w in OUTSIDE_GRO):
        return {"offers": [], "note": "The General Register Office covers England and Wales. "
                "Records for this place are held elsewhere: see Where to look next."}  # fmt: skip
    if year is not None and year < 1837:
        return {"offers": [], "note": "Civil registration in England and Wales began in 1837. "
                "Before then, look for parish registers: see Where to look next."}  # fmt: skip
    out = []
    for o in offers():
        if event not in o["events"]:
            continue
        span = o["years"].get(event)
        if span and year is not None and not (span[0] <= year <= span[1]):
            continue
        out.append({**o, "total_pence": sum(f["pence"] for f in o["fees"])})
    note = ""
    if out and year is not None and ((event == "birth" and year <= 1934) or
                                     (event == "death" and year <= 1957)):  # fmt: skip
        note = ("Find the GRO index reference first: it's free in the GRO's online index, and "
                "on FreeBMD. A PDF or online view needs one.")  # fmt: skip
    return {"offers": out, "note": note}
