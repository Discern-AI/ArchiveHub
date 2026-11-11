"""Lineages: who held a role at a place or organisation, one after another.

A lineage is the claims with a role (licensee, owner, tenant, vicar...) about one subject,
in date order, each keeping its evidence. Nothing is guessed:
- Years nobody is recorded for are shown as gaps, not filled in.
- Recent holders may still be living, so their names are hidden by default.
- A holder whose name and dates fit someone in the user's family tree is suggested as
  possibly the same person, never linked automatically.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from history import queries
from history.models import Assertion, LivingStatus, Organisation, Person, Place
from projects.permissions import visible_projects

ROLES = {
    "licensee": "Licensees",
    "landlord": "Landlords",
    "proprietor": "Proprietors",
    "owner": "Owners",
    "tenant": "Tenants",
    "occupier": "Occupiers",
    "vicar": "Vicars",
    "rector": "Rectors",
    "minister": "Ministers",
    "headteacher": "Headteachers",
    "master": "Masters",
    "mayor": "Mayors",
}
# Someone holding a role this recently may still be alive: an adult (18) then, born
# within the last 110 years, is treated as living everywhere else in ArchiveHub.
RECENT_YEARS = 92
ADULT_AT = 16


def _sources(a: Assertion) -> list[dict[str, str]]:
    return [
        {"title": e.title, "url": e.url, "source": e.source_name, "what_it_says": e.note}
        for e in a.evidence.all()
    ]


def _words(name: str) -> list[str]:
    return re.findall(r"[a-z]+", name.lower())


def _same_name(holder: str, person: str) -> str:
    """Why a holder's name might be this person's, or '' if it doesn't fit."""
    h, p = _words(holder), _words(person)
    if len(h) < 2 or len(p) < 2 or h[-1] != p[-1]:
        return ""
    if h[0] == p[0]:
        return "same first name and surname"
    if len(h[0]) == 1 and p[0].startswith(h[0]):
        return "same surname, matching initial"
    return ""


def _connections(user, holder: str, start: int | None, end: int | None) -> list[dict[str, Any]]:
    from genealogy.exporter import current_values

    if start is None and end is None:
        return []
    surname = _words(holder)[-1] if _words(holder) else ""
    if not surname:
        return []
    out = []
    people = Person.objects.filter(
        project__in=visible_projects(user), living_status=LivingStatus.DECEASED,
        name__icontains=surname,
    ).select_related("project")  # fmt: skip
    for p in people[:200]:
        v = current_values(p.project, [p.id]).get(p.id, {})
        name = v["name"].value if "name" in v else p.name
        why = _same_name(holder, name)
        if not why:
            continue
        b = v.get("birth date") or v.get("baptism date")
        d = v.get("death date") or v.get("burial date")
        born = (b.year_from or b.year_to) if b else None
        died = (d.year_to or d.year_from) if d else None
        first, last = start or end, end or start
        if born and last < born + ADULT_AT:
            continue  # too young to hold it
        if died and first > died:
            continue  # already dead
        reasons = [why]
        if born or died:
            reasons.append(f"alive then ({born or '?'}–{died or '?'})")
        out.append({
            "project": p.project.title,
            "project_id": str(p.project_id),
            "person_id": str(p.id),
            "name": name,
            "reason": "; ".join(reasons),
        })  # fmt: skip
    return out


def succession(user, subject, role: str) -> dict[str, Any]:
    grouped = queries.claims_about(user, subject)
    claims = next((c for p, c in grouped.items() if p.lower() == role), [])
    cutoff = date.today().year - RECENT_YEARS
    holders, hidden = [], 0
    for a in sorted(claims, key=lambda a: (a.year_from or a.year_to or 99999, a.value)):
        start, end = a.year_from, a.year_to if a.year_to is not None else a.year_from
        recent = (end or start or 0) > cutoff
        if recent:
            hidden += 1
        holders.append({
            "id": str(a.id),
            "name": None if recent else a.value,
            "hidden": recent,
            "year_from": start,
            "year_to": end,
            "date_text": a.date_text,
            "status": a.status,
            "sources": _sources(a),
            "connections": [] if recent else _connections(user, a.value, start, end),
        })  # fmt: skip
    gaps = []
    dated = [h for h in holders if h["year_from"] or h["year_to"]]
    for prev, nxt in zip(dated, dated[1:], strict=False):
        last = prev["year_to"] or prev["year_from"]
        first = nxt["year_from"] or nxt["year_to"]
        if first - last > 1:
            gaps.append({"from": last + 1, "to": first - 1})
    return {
        "subject": {"id": str(subject.pk), "name": subject.name, "type": subject._meta.model_name},
        "role": role,
        "role_label": ROLES.get(role, role.capitalize()),
        "holders": holders,
        "gaps": gaps,
        "hidden_recent": hidden,
        "notes": [
            "Each name is from a record; years in between with nobody recorded are shown "
            "as gaps, not guessed.",
            *(
                [
                    f"{hidden} recent holder{'s' if hidden != 1 else ''} may still be living, so "
                    "names are hidden."
                ]
                if hidden
                else []
            ),
            "A holder who may be someone in your family tree is only suggested: check the "
            "records before linking them.",
        ],  # fmt: skip
    }


def lineage_subjects(user) -> list[dict[str, Any]]:
    """Places and organisations with any role recorded, for browsing."""
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Q

    visible = Q(project__isnull=True) | Q(project__in=visible_projects(user))
    out = []
    for model in (Organisation, Place):
        ct = ContentType.objects.get_for_model(model)
        rows = Assertion.objects.filter(
            visible, subject_type=ct, predicate__in=list(ROLES)
        ).values_list("subject_id", "predicate")
        roles: dict[Any, dict[str, int]] = {}
        for sid, pred in rows:
            roles.setdefault(sid, {})
            roles[sid][pred] = roles[sid].get(pred, 0) + 1
        for obj in model.objects.filter(pk__in=list(roles)):
            out.append({
                "type": model._meta.model_name,
                "id": str(obj.pk),
                "name": obj.name,
                "kind": getattr(obj, "kind", ""),
                "roles": [{"role": r, "label": ROLES[r], "count": n}
                          for r, n in sorted(roles[obj.pk].items())],
            })  # fmt: skip
    return sorted(out, key=lambda s: s["name"])
