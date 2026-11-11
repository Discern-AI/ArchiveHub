"""Culture links and the Life Report.

Matching uses only a person's documented details (their occupation, places and dates),
never assumptions about class. Each match says why it was chosen, and every item is
labelled as showing their world, not them. Only curator-approved items are used, and an
image is shown only when its rights are open; otherwise the item is linked.

The Life Report is built from the Life Story, Life and times and up to three culture
items. It's written from the records, without AI, so it costs no credits.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from genealogy.context import life_and_times
from genealogy.exporter import current_values
from genealogy.life_story import life_story
from history.models import LivingStatus, Person

from .models import CultureItem, ItemStatus, Rights

DATA = Path(__file__).parent / "data" / "items.json"

# What kinds of work an occupation involves, so a match is on documented work, not class.
WORK = {
    "labourer": ["farm work", "harvest", "haymaking", "plough", "ploughing", "reaping"],
    "agricultural": ["farm work", "harvest", "haymaking", "plough", "ploughing", "reaping"],
    "ag lab": ["farm work", "harvest", "haymaking", "plough", "ploughing", "reaping"],
    "farm": ["farm work", "harvest", "haymaking", "plough", "ploughing", "reaping"],
    "farmer": ["farm work", "harvest", "plough", "ploughing"],
    "ploughman": ["plough", "ploughing", "farm work"],
    "carter": ["farm work", "harvest"],
    "shepherd": ["farm work", "countryside"],
    "publican": ["inn"],
    "innkeeper": ["inn"],
    "licensed victualler": ["inn"],
    "beer seller": ["inn"],
    "victualler": ["inn"],
}
SAY = {"plough": "a plough", "harvest": "the harvest", "inn": "an inn", "fields": "fields"}
TEXT_KINDS = {"rhyme", "ballad", "tale", "song"}
ENGLAND = {"england", "english", "british", "britain", "wales", "scotland"}


def load_items() -> int:
    """Load the checked starter items as approved (their rights were read at the source)."""
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for row in data["items"]:
        row = dict(row)
        key = row.pop("key")
        row["rights_checked_on"] = date.fromisoformat(row["rights_checked_on"])
        CultureItem.objects.update_or_create(
            key=key, defaults={**row, "status": ItemStatus.APPROVED}
        )
    return len(data["items"])


def _facts(project, person: Person) -> dict[str, Any]:
    v = current_values(project, [person.id]).get(person.id, {})

    def year(*labels):
        for label in labels:
            a = v.get(f"{label} date")
            if a and (a.year_from or a.year_to):
                return a.year_from or a.year_to
        return None

    places = " ".join(v[f"{e} place"].value for e in ("birth", "death") if v.get(f"{e} place"))
    return {
        "name": v["name"].value if "name" in v else person.name,
        "occupation": v["occupation"].value if v.get("occupation") else "",
        "born": year("birth", "baptism"),
        "died": year("death", "burial"),
        "places": places,
    }


def match_items(project, person: Person, limit: int = 3) -> list[dict[str, Any]]:
    f = _facts(project, person)
    occupation = f["occupation"].lower()
    work = sorted({w for k, ws in WORK.items() if k in occupation for w in ws})
    first = f["name"].split()[0] if f["name"].split() else "they"
    lived_from, lived_to = f["born"], f["died"] or (f["born"] + 80 if f["born"] else None)
    in_england = any(w in f["places"].lower() for w in ("england", "berkshire", "wales",
                                                        "shire", "london", "oxford"))  # fmt: skip
    out = []
    for item in CultureItem.objects.filter(status=ItemStatus.APPROVED):
        reasons, score = [], 0
        shared = [s for s in item.subjects if s in work]
        if shared:
            score += 3
            reasons.append(f"It shows {SAY.get(shared[0], shared[0])}, the kind of work recorded "
                           f"for {first} ({f['occupation'].lower()}).")  # fmt: skip
        if not shared:
            continue  # without a documented link to their life, it isn't chosen
        # A traditional rhyme's printing date isn't when it was made up.
        if item.kind in TEXT_KINDS:
            made_word = f"This version was printed in {item.made_from}"
        else:
            made_word = f"It was made in {item.made_text}"
        if item.made_from and lived_from:
            made = item.made_from
            if lived_from <= made <= (lived_to or made):
                score += 2
                reasons.append(f"{made_word}, during {first}'s lifetime.")
            elif abs(made - lived_from) <= 60:
                score += 1
                when = "before" if made < lived_from else "after"
                reasons.append(f"{made_word}, about {abs(made - lived_from)} "
                               f"years {when} {first} was born.")  # fmt: skip
            else:
                reasons.append(f"{made_word}, a long way from {first}'s time.")
        if item.kind in TEXT_KINDS:
            reasons.append("The rhyme itself is traditional and may be much older.")
        if item.country.lower() in ENGLAND:
            if in_england:
                score += 2
                reasons.append("It's English, like the places in their records.")
        else:
            reasons.append(
                f"It's from {item.country}: a comparison from abroad, not their country."
            )
        if item.rights == Rights.OPEN:
            score += 1
        out.append({"item": item, "score": score, "reasons": reasons})
    out.sort(key=lambda m: (-m["score"], m["item"].made_from or 0))
    # Variety: pictures and words both, so a report isn't all prints or all rhymes.
    chosen, kinds = [], {}
    for m in out:
        kind = "text" if m["item"].text else "image"
        if kinds.get(kind, 0) >= (limit + 1) // 2:
            continue
        kinds[kind] = kinds.get(kind, 0) + 1
        chosen.append(m)
        if len(chosen) == limit:
            break
    return chosen


def item_block(item: CultureItem, reasons: list[str]) -> dict[str, Any]:
    show_image = item.rights == Rights.OPEN and bool(item.image_url)
    quote = item.rights == Rights.OPEN and bool(item.text)
    return {
        "type": "culture",
        "key": item.key,
        "kind": item.kind,
        "title": item.title,
        "creator": item.creator,
        "made": item.made_text,
        "description": item.description,
        "image_url": item.image_url if show_image else "",
        "text": item.text if quote else "",
        "link_only": not (show_image or quote),
        "source_name": item.source_name,
        "source_url": item.source_url,
        "credit": item.credit,
        "licence": item.licence,
        "why": " ".join(reasons),
        "label": "This shows their world, not them. "
        + ("Artists often made country life look more picturesque than it was."
           if not item.text else ""),
    }  # fmt: skip


def build_report(project, person: Person, length: str = "short") -> dict[str, Any]:
    if person.living_status != LivingStatus.DECEASED:
        return {"private": True, "note": "Life Reports are only written for people who have died."}
    story = life_story(project, person)
    blocks: list[dict[str, Any]] = [
        {"type": "title", "text": story["person"]["name"]},
        {"type": "glance", **story["at_a_glance"]},
    ]
    years = [e["year"] for c in story["chapters"] for e in c["events"] if e["year"]]
    for c in story["chapters"]:
        events = c["events"] if length == "long" else c["events"][:3]
        blocks.append({"type": "heading", "text": c["title"]})
        blocks.append({
            "type": "paragraph",
            "text": " ".join(e["sentence"] for e in events),
            "sources": [s for e in events for s in e["sources"]][:6],
            "status": "documented" if all(e["status"] == "documented" for e in events) else "mixed",
        })  # fmt: skip
    if years:
        mid = min(years) + 30 if len(years) == 1 else (min(years) + max(years)) // 2
        lt = life_and_times(mid, project)
        lines = [x for x in (lt["money"].get("sentence"), lt["weather"].get("sentence")) if x]
        lines += [f"{h['title']} ({h['date_text']}): {h['when']}." for h in lt["happening"][:4]]
        blocks.append({"type": "heading", "text": "The world around them"})
        blocks.append({"type": "context", "year": mid, "lines": lines,
                       "label": lt["label"]})  # fmt: skip
    matches = match_items(project, person, 3 if length == "long" else 2)
    if matches:
        blocks.append({"type": "heading", "text": "How artists and writers saw their world"})
        blocks += [item_block(m["item"], m["reasons"]) for m in matches]
    blocks.append({"type": "heading", "text": "Sources and gaps"})
    blocks.append(
        {"type": "gaps", "lines": story["gaps"] or ["No obvious gaps in the main facts."]}
    )
    return {
        "private": False,
        "person": story["person"],
        "length": length,
        "blocks": blocks,
        "items": [m["item"].key for m in matches],
        "cost": "Free: written from the records, without AI.",
        "note": "Edit any text before saving. Nothing is published.",
    }
