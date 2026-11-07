"""Tree health check: things in a family tree worth a second look.

Each finding says what looked odd and why, using the facts currently in use (corrections
win over imports). Nothing is changed, merged or hidden: these are prompts for a person
to check, and many will turn out to be right (ADR-040).
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any

from history.models import LivingStatus, Person

from .exporter import current_values
from .models import RelationKind, Relationship

YOUNGEST_PARENT = 13
OLDEST_MOTHER = 55
OLDEST_FATHER = 80
LONGEST_LIFE = 105
DUPLICATE_YEARS = 2


def _years(a) -> tuple[int | None, int | None]:
    """(earliest, latest) years a dated claim allows."""
    if a is None:
        return None, None
    lo = a.year_from if a.year_from is not None else a.year_to
    hi = a.year_to if a.year_to is not None else a.year_from
    return lo, hi


def _key(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z]+", plain))


def check_tree(project) -> dict[str, Any]:
    people = {p.id: p for p in Person.objects.filter(project=project)}
    values = current_values(project, list(people))

    def name(pid) -> str:
        v = values.get(pid, {})
        return v["name"].value if "name" in v else people[pid].name

    def born(pid):
        v = values.get(pid, {})
        return _years(v.get("birth date") or v.get("baptism date"))

    def died(pid):
        v = values.get(pid, {})
        return _years(v.get("death date") or v.get("burial date"))

    def who(*ids) -> list[dict[str, str]]:
        return [{"id": str(i), "name": name(i)} for i in ids]

    findings: list[dict[str, Any]] = []

    def add(kind: str, title: str, detail: str, ids) -> None:
        findings.append({"kind": kind, "title": title, "detail": detail, "people": who(*ids)})

    # One person's own dates.
    for pid in people:
        b_lo, b_hi = born(pid)
        d_lo, d_hi = died(pid)
        if b_lo is not None and d_hi is not None and d_hi < b_lo:
            add(
                "dates",
                "Died before being born",
                f"Born {b_lo} at the earliest, died {d_hi} at the latest.",
                [pid],
            )
        elif b_hi is not None and d_lo is not None and d_lo - b_hi > LONGEST_LIFE:
            add(
                "dates",
                "Very long life",
                f"At least {d_lo - b_hi} years between birth and death.",
                [pid],
            )

    # Parents and children.
    parents_of: dict[Any, list] = defaultdict(list)
    links = Relationship.objects.filter(project=project)
    for r in links.filter(kind=RelationKind.PARENT):
        parents_of[r.relative_id].append(r.person_id)
    for child, parents in parents_of.items():
        c_lo, c_hi = born(child)
        if c_lo is None:
            continue
        for parent in parents:
            p_lo, p_hi = born(parent)
            pd_lo, pd_hi = died(parent)
            sex = people[parent].sex
            if p_lo is not None and c_hi is not None and c_hi - p_lo < YOUNGEST_PARENT:
                add(
                    "parents",
                    "Very young parent",
                    f"{name(parent)} would have been at most {c_hi - p_lo} "
                    f"when {name(child)} was born.",
                    [parent, child],
                )
            elif p_hi is not None:
                oldest = OLDEST_MOTHER if sex == "F" else OLDEST_FATHER
                if c_lo - p_hi > oldest:
                    add(
                        "parents",
                        "Unusually old parent",
                        f"{name(parent)} would have been at least {c_lo - p_hi} "
                        f"when {name(child)} was born.",
                        [parent, child],
                    )
            # A father can die before a birth (up to about a year); a mother can't.
            grace = 0 if sex == "F" else 1
            if pd_hi is not None and c_lo > pd_hi + grace:
                add(
                    "parents",
                    "Born after a parent's death",
                    f"{name(child)} was born {c_lo} at the earliest; "
                    f"{name(parent)} died {pd_hi} at the latest.",
                    [parent, child],
                )

    # Possible duplicates: same name, births within a couple of years. Never merged.
    by_name: dict[str, list] = defaultdict(list)
    for pid in people:
        by_name[_key(name(pid))].append(pid)
    for group in by_name.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                a_lo, a_hi = born(a)
                b_lo, b_hi = born(b)
                if a_lo is None or b_lo is None:
                    continue
                if abs(a_lo - b_lo) <= DUPLICATE_YEARS:
                    add(
                        "duplicates",
                        "Possibly the same person",
                        f"Same name, born {a_lo} and {b_lo}. They may be one person entered twice, "
                        "or two different people: only a person can decide.",
                        [a, b],
                    )

    # Branches that don't connect to the rest of the tree.
    neighbours: dict[Any, set] = defaultdict(set)
    for r in links:
        neighbours[r.person_id].add(r.relative_id)
        neighbours[r.relative_id].add(r.person_id)
    seen: set = set()
    groups = []
    for pid in people:
        if pid in seen:
            continue
        stack, group = [pid], []
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            group.append(cur)
            stack.extend(neighbours[cur] - seen)
        groups.append(group)
    groups.sort(key=len, reverse=True)
    for group in groups[1:]:
        if len(group) == 1:
            add(
                "branches",
                "Not connected to anyone",
                "No parent, partner or child recorded.",
                group,
            )
        else:
            add(
                "branches",
                f"A separate branch of {len(group)} people",
                "This group isn't linked to the main tree.",
                group[:5],
            )

    # Gaps: deceased people with no dates at all.
    no_dates = [
        pid
        for pid, p in people.items()
        if p.living_status == LivingStatus.DECEASED
        and born(pid) == (None, None)
        and died(pid) == (None, None)
    ]
    if no_dates:
        add(
            "gaps",
            f"{len(no_dates)} people with no dates",
            "No birth, baptism, death or burial date recorded.",
            no_dates[:10],
        )

    order = {"dates": 0, "parents": 1, "duplicates": 2, "branches": 3, "gaps": 4}
    findings.sort(key=lambda f: order[f["kind"]])
    return {
        "people": len(people),
        "branches": len(groups),
        "findings": findings,
        "note": "These are things to check, not errors: many will turn out to be right. "
        "Nothing has been changed or merged.",
    }
