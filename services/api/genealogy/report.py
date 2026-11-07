"""What a GEDCOM import brought in, and what it left behind.

A GEDCOM export isn't a complete copy of someone's online tree: media are often only
references, and every program writes its own extra tags. People should see exactly what
came across, so nothing is silently lost.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .gedcom import EVENTS, Node

# Individual tags the importer turns into people, facts and relationships.
USED_INDI = {"NAME", "SEX", "OCCU", "FAMS", "FAMC", *EVENTS}
USED_FAM = {"HUSB", "WIFE", "CHIL", "MARR"}
TAG_NAMES = {
    "RESI": "residences",
    "CENS": "census entries",
    "EMIG": "emigrations",
    "IMMI": "immigrations",
    "NATU": "naturalisations",
    "PROB": "probates",
    "WILL": "wills",
    "GRAD": "graduations",
    "EDUC": "education",
    "MILI": "military service (non-standard tag)",
    "_MILT": "military service (non-standard tag)",
    "RELI": "religion",
    "TITL": "titles",
    "EVEN": "other events",
    "FACT": "other facts",
    "DIV": "divorces",
    "ENGA": "engagements",
    "MARB": "marriage banns",
    "ADOP": "adoptions",
    "CREM": "cremations",
}


def _walk(nodes: list[Node]):
    for n in nodes:
        yield n
        yield from _walk(n.children)


def import_report(records: list[Node]) -> dict[str, Any]:
    head = next((r for r in records if r.tag == "HEAD"), None)
    gedc = head.first("GEDC") if head else None
    everything = list(_walk([r for r in records if r.tag not in ("HEAD", "TRLR")]))
    left_out: Counter[str] = Counter()
    for r in records:
        if r.tag == "INDI":
            for c in r.children:
                if c.tag not in USED_INDI and c.tag not in ("SOUR", "OBJE", "NOTE"):
                    left_out[TAG_NAMES.get(c.tag, f"{c.tag} entries")] += 1
        elif r.tag == "FAM":
            for c in r.children:
                if c.tag not in USED_FAM and c.tag not in ("SOUR", "OBJE", "NOTE"):
                    left_out[TAG_NAMES.get(c.tag, f"family {c.tag} entries")] += 1
    media = [n for n in everything if n.tag == "OBJE"]
    files = [n for n in everything if n.tag == "FILE"]
    return {
        "gedcom_version": gedc.text("VERS") if gedc else "",
        "made_by": head.text("SOUR") if head else "",
        "source_citations_not_imported": sum(
            1 for n in everything if n.tag == "SOUR" and n.level > 0
        ),
        "source_records_not_imported": sum(1 for r in records if r.tag == "SOUR"),
        "notes_not_imported": sum(1 for n in everything if n.tag == "NOTE" and n.level > 0),
        "media_references": len(media),
        "media_files_named": len(files),
        "media_note": (
            "Media in a GEDCOM file are usually references to files kept elsewhere, not the "
            "files themselves. Upload the photos and documents to the Archive separately."
            if media
            else ""
        ),
        "other_facts_not_imported": dict(sorted(left_out.items(), key=lambda kv: -kv[1])),
    }
