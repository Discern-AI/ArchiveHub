"""A person's life told in order, built only from the tree's own facts.

Every sentence comes from a recorded fact (or a family link) and carries its sources and
how sure it is. Nothing is invented: a missing date or place is left out and listed as a
gap to look into. What was happening in the world is kept apart, as context, never as a
fact about the person. Living people's lives aren't told; living relatives are mentioned
without names or dates.
"""

from __future__ import annotations

import re
from typing import Any

from history.models import Assertion, LivingStatus, Person

from .exporter import current_values
from .models import OverlayEvent, RelationKind, Relationship, Residence

MONTHS = {
    "JAN": "January", "FEB": "February", "MAR": "March", "APR": "April", "MAY": "May",
    "JUN": "June", "JUL": "July", "AUG": "August", "SEP": "September", "OCT": "October",
    "NOV": "November", "DEC": "December",
}  # fmt: skip
QUALIFIERS = {"ABT": "about", "CAL": "about", "EST": "about", "BEF": "before", "AFT": "after"}
CHAPTERS = [
    ("early", "Early life"),
    ("family", "Marriage and family"),
    ("work", "Work and homes"),
    ("later", "Later life"),
]


def say_date(text: str) -> str:
    """'ABT 1850' -> 'about 1850'; '14 MAR 1988' -> '14 March 1988'; ranges in words."""
    t = " ".join(text.strip().split())
    if not t:
        return ""
    up = t.upper()
    m = re.fullmatch(r"(BET|FROM) (.+) (AND|TO) (.+)", up)
    if m:
        return f"between {say_date(m.group(2))} and {say_date(m.group(4))}"
    words = up.split()
    if words and words[0] in QUALIFIERS:
        return f"{QUALIFIERS[words[0]]} {say_date(' '.join(t.split()[1:]))}"
    if all(w in MONTHS or w.isdigit() for w in words):
        return " ".join(MONTHS.get(w, w.lstrip("0") or "0") for w in words)
    return t  # wording we can't parse is kept as written ("summer 1952")


def phrase(d: str) -> str:
    """A spoken date with its preposition: 'on 14 March 1988', 'in 1850', 'about 1850'."""
    if not d:
        return ""
    if d.split()[0] in ("about", "before", "after", "between"):
        return f" {d}"
    return f" {'on' if len(d.split()) == 3 else 'in'} {d}"


def _when(a: Assertion | None) -> str:
    return phrase(say_date(a.date_text or a.value)) if a is not None else ""


def _year(a: Assertion | None) -> int | None:
    if a is None:
        return None
    return a.year_from if a.year_from is not None else a.year_to


def _sources(claims: list[Assertion]) -> list[dict[str, str]]:
    out, seen = [], set()
    for a in claims:
        for e in a.evidence.all():
            key = (e.title, e.url)
            if key in seen:
                continue
            seen.add(key)
            out.append({"title": e.title, "url": e.url, "source": e.source_name,
                        "what_it_says": e.note})  # fmt: skip
    return out


def _status(claims: list[Assertion]) -> str:
    statuses = {a.status for a in claims}
    for s in ("disputed", "inferred", "remembered"):
        if s in statuses:
            return s
    return "documented"


def life_story(project, person: Person) -> dict[str, Any]:
    if person.living_status != LivingStatus.DECEASED:
        return {
            "person": {"id": str(person.id), "name": person.name},
            "private": True,
            "note": "Living people's lives aren't told here: their details are private.",
        }
    links = list(
        Relationship.objects.filter(project=project, person=person).select_related("relative")
    ) + list(Relationship.objects.filter(project=project, relative=person).select_related("person"))
    parents = [
        r.person for r in links if r.kind == RelationKind.PARENT and r.relative_id == person.id
    ]
    children = [
        r.relative for r in links if r.kind == RelationKind.PARENT and r.person_id == person.id
    ]
    partners = [
        (r.relative if r.person_id == person.id else r.person, r)
        for r in links
        if r.kind == RelationKind.SPOUSE
    ]
    everyone = [person, *parents, *children, *(p for p, _ in partners)]
    values = current_values(project, [p.id for p in everyone])
    v = values.get(person.id, {})

    def name_of(p: Person) -> str:
        pv = values.get(p.id, {})
        return pv["name"].value if "name" in pv else p.name

    name = name_of(person)
    first = name.split()[0] if name.split() else name
    events: list[dict[str, Any]] = []

    def add(chapter, year, sentence, claims=(), people=(), kind="", extra_sources=()):
        claims = [c for c in claims if c is not None]
        events.append({
            "chapter": chapter,
            "year": year,
            "kind": kind,
            "sentence": sentence,
            "status": _status(claims) if claims else "documented",
            "claim_ids": [str(c.id) for c in claims],
            "sources": _sources(claims) + list(extra_sources),
            "people": [{"id": str(p.id), "name": name_of(p)} for p in people],
        })  # fmt: skip

    def place(label: str) -> tuple[str, Assertion | None]:
        a = v.get(f"{label} place")
        return (f" in {a.value}" if a else ""), a

    birth, birth_year = v.get("birth date"), _year(v.get("birth date"))
    if birth or v.get("birth place"):
        where, pa = place("birth")
        add(
            "early",
            birth_year,
            f"{first} was born{_when(birth)}{where}.",
            [birth, pa],
            kind="birth",
        )
    bap = v.get("baptism date")
    if bap or v.get("baptism place"):
        where, pa = place("baptism")
        add("early", _year(bap), f"Baptised{_when(bap)}{where}.", [bap, pa], kind="baptism")
    file_source = {"title": "The imported family tree", "url": "", "source": "Family link",
                   "what_it_says": ""}  # fmt: skip
    if parents:
        names = " and ".join(name_of(p) for p in parents)
        add("early", birth_year, f"Child of {names}.", people=parents, kind="parents",
            extra_sources=[file_source])  # fmt: skip

    for partner, rel in partners:
        f = rel.fields or {}
        if partner.living_status != LivingStatus.DECEASED:
            add("family", None, "Had a partner who may still be living (details private).",
                kind="partner", extra_sources=[file_source])  # fmt: skip
            continue
        when = phrase(say_date(f.get("marriage_date", "")))
        at = f" at {f['marriage_place']}" if f.get("marriage_place") else ""
        years = re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", f.get("marriage_date", ""))
        if when or at:
            sentence = f"Married {name_of(partner)}{when}{at}."
        else:
            sentence = f"Partner of {name_of(partner)} (no marriage date recorded)."
        add("family", int(years[0]) if years else None, sentence, people=[partner], kind="marriage",
            extra_sources=[file_source])  # fmt: skip

    living_children = [c for c in children if c.living_status != LivingStatus.DECEASED]
    if living_children:
        n = len(living_children)
        sentence = (
            "Had a child who may still be living (details private)."
            if n == 1
            else f"Had {n} children who may still be living (details private)."
        )
        add("family", None, sentence, kind="child", extra_sources=[file_source])
    for child in children:
        cv = values.get(child.id, {})
        if child.living_status != LivingStatus.DECEASED:
            continue
        word = {"M": "son", "F": "daughter"}.get(child.sex, "child")
        b = cv.get("birth date")
        add("family", _year(b), f"Their {word} {name_of(child)} was born{_when(b)}.", [b],
            people=[child], kind="child")  # fmt: skip

    occ = v.get("occupation")
    if occ:
        job = occ.value.strip()
        # "PUBLICAN", "Publican" and "Agricultural labourer" read as "a publican"; a title with
        # other capitals may hold a proper name ("Royal Navy officer"), so it's kept.
        words = job.split()
        if job.isupper():
            job = job.lower()
        elif words and words[0][1:].islower() and all(w.islower() for w in words[1:]):
            job = job[0].lower() + job[1:]  # "Agricultural labourer": just sentence case
        article = "an" if job[:1].lower() in "aeiou" else "a"
        add("work", None, f"Worked as {article} {job}.", [occ], kind="occupation")
    for r in Residence.objects.filter(person=person):
        when = f" in {say_date(r.date_text)}" if r.date_text else ""
        src = {"title": r.source_file.name if r.source_file else "Added by hand",
               "url": "", "source": "Residence record", "what_it_says": r.note}  # fmt: skip
        add("work", r.year_from or r.year_to, f"Recorded living in {r.place_text}{when}.",
            kind="residence", extra_sources=[src])  # fmt: skip

    death, death_year = v.get("death date"), _year(v.get("death date"))
    if death or v.get("death place"):
        where, pa = place("death")
        age = ""
        if birth_year and death_year and death.year_from and death.year_to == death.year_from:
            age = f", aged about {death_year - birth_year}"
        add(
            "later",
            death_year,
            f"{first} died{_when(death)}{where}{age}.",
            [death, pa],
            kind="death",
        )
    bur = v.get("burial date")
    if bur or v.get("burial place"):
        where, pa = place("burial")
        add("later", _year(bur), f"Buried{_when(bur)}{where}.", [bur, pa], kind="burial")

    events.sort(key=lambda e: (e["year"] is None, e["year"] or 0))
    chapters = [
        {"key": key, "title": title, "events": [e for e in events if e["chapter"] == key]}
        for key, title in CHAPTERS
    ]
    chapters = [c for c in chapters if c["events"]]

    gaps = []
    if not birth:
        gaps.append("No birth or baptism date recorded.")
    if not death and not v.get("burial date"):
        gaps.append("No death or burial date recorded.")
    if not parents:
        gaps.append("No parents recorded.")
    if not occ:
        gaps.append("No occupation recorded.")
    if not Residence.objects.filter(person=person).exists():
        gaps.append("No addresses recorded (censuses list where people lived).")

    context = []
    end = death_year or (_year(bur) if bur else None)

    def age(years: int) -> str:
        return "under 1" if years <= 0 else f"about {years}"

    if birth_year and end:
        for o in OverlayEvent.objects.filter(project=None, kind__in=["war", "law", "records"]):
            to = o.year_to or o.year_from
            if not (o.year_from <= end and to >= birth_year):
                continue
            if o.kind == "records" and o.title != "Census":
                continue  # registration starting, a census lost: not part of their life
            a, b = max(o.year_from, birth_year) - birth_year, min(to, end) - birth_year
            context.append({
                "title": o.title,
                "date_text": o.date_text,
                "area": o.area,
                "age": age(a) if a == b else f"{age(a)} to {b}",
                "note": "They could appear in it." if o.title == "Census" else "",
                "source_title": o.source_title,
                "source_url": o.source_url,
            })  # fmt: skip

    glance = {
        "born": f"{say_date(birth.date_text or birth.value) if birth else ''}"
        f"{', ' + v['birth place'].value if v.get('birth place') else ''}".strip(", "),
        "died": f"{say_date(death.date_text or death.value) if death else ''}"
        f"{', ' + v['death place'].value if v.get('death place') else ''}".strip(", "),
        "occupation": occ.value if occ else "",
        "partners": len(partners),
        "children": len(children),
    }
    return {
        "person": {"id": str(person.id), "name": name},
        "private": False,
        "at_a_glance": glance,
        "chapters": chapters,
        "context": context,
        "context_note": "What was happening while they lived, for context. It doesn't say "
        "they took part.",
        "gaps": gaps,
    }
