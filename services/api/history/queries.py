"""Read helpers for the history layer. All visibility rules for claims live here.

Shared reference claims (no project) are visible to everyone signed in. Project claims
are visible only to people who can see that project.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet

from projects.permissions import visible_projects

from .models import Assertion, Organisation, Person, Place, Source, SourceRecord

WORD = re.compile(r"[a-z0-9&]+")
STOP = {
    "the", "a", "an", "of", "in", "on", "at", "and", "or", "for", "to", "was", "is", "what",
    "when", "where", "who", "did", "does", "do", "how", "about", "find", "any",
    # Too common in this domain to tell sources apart.
    "record", "records", "history", "historical", "information", "uk",
}  # fmt: skip


def terms(text: str) -> list[str]:
    return [t for t in WORD.findall(text.lower()) if t not in STOP and len(t) > 1]


def score(text_fields: list[str], query_terms: list[str]) -> int:
    hay = " ".join(f or "" for f in text_fields).lower()
    return sum(1 for t in query_terms if t in hay)


def min_score(query_terms: list[str]) -> int:
    """Longer queries must match more than one word to count."""
    return 1 if len(query_terms) <= 2 else 2


def visible_assertions(user) -> QuerySet[Assertion]:
    return Assertion.objects.filter(Q(project__isnull=True) | Q(project__in=visible_projects(user)))


def search_sources(query: str, record_type: str | None = None, limit: int = 8) -> list[Source]:
    q = terms(query + " " + (record_type or ""))
    scored = []
    for s in Source.objects.all():
        fields = [s.name, s.holder, s.description, s.coverage_area, s.kind, s.plan]
        fields += [" ".join(s.record_types), " ".join(s.tags)]
        n = score(fields, q)
        if n and n >= min_score(q):
            scored.append((n, s))
    scored.sort(key=lambda pair: (-pair[0], pair[1].name))
    return [s for _, s in scored[:limit]]


@dataclass
class Subject:
    obj: object
    kind: str
    name: str
    alt_names: list[str] = field(default_factory=list)


def find_subjects(name: str, user=None, limit: int = 5) -> list[Subject]:
    q = terms(name)
    if not q:
        return []
    found: list[tuple[int, Subject]] = []
    for model, kind in ((Organisation, "organisation"), (Place, "place"), (Person, "person")):
        qs = model.objects.all()
        if model is Person:
            # Only shared people and people in projects this user can see; never living people.
            visible = Q(project__isnull=True)
            if user is not None and user.is_authenticated:
                visible |= Q(project__in=visible_projects(user))
            qs = qs.filter(visible).exclude(living_status="living")
        for obj in qs:
            names = [obj.name, *obj.alt_names]
            n = score(names, q)
            if n:
                found.append((n, Subject(obj, kind, obj.name, obj.alt_names)))
    found.sort(key=lambda pair: -pair[0])
    return [s for _, s in found[:limit]]


def search_records(
    query: str, year_from: int | None = None, year_to: int | None = None, limit: int = 10
) -> list[SourceRecord]:
    q = terms(query)
    if not q:
        return []
    scored = []
    for r in SourceRecord.objects.select_related("source", "place"):
        if year_from and r.year_to and r.year_to < year_from:
            continue
        if year_to and r.year_from and r.year_from > year_to:
            continue
        place = str(r.place) if r.place else ""
        n = score([r.title, r.summary, r.record_type, place, r.source.name], q)
        if n and n >= min_score(q):
            scored.append((n, r))
    scored.sort(key=lambda pair: (-pair[0], pair[1].title))
    return [r for _, r in scored[:limit]]


def claims_about(user, subject_obj, predicate: str | None = None) -> dict[str, list[Assertion]]:
    """Claims about one subject, grouped by predicate, with evidence prefetched."""
    ct = ContentType.objects.get_for_model(subject_obj)
    qs = visible_assertions(user).filter(subject_type=ct, subject_id=subject_obj.pk)
    if predicate:
        qs = qs.filter(predicate__iexact=predicate)
    qs = qs.prefetch_related(
        "evidence__record__source", "evidence__file", "evidence__basket_item"
    ).order_by("predicate", "year_from")
    grouped: dict[str, list[Assertion]] = defaultdict(list)
    for a in qs:
        grouped[a.predicate].append(a)
    return dict(grouped)


def is_disputed(claims: list[Assertion]) -> bool:
    """Sources disagree when the same question has more than one distinct answer."""
    values = {c.value.strip().lower() for c in claims}
    return len(values) > 1 and any(c.predicate in SINGLE_VALUED for c in claims)


# Predicates where two different answers are a conflict (a pub can have many licensees).
SINGLE_VALUED = {"address", "first recorded", "last listed", "demolished", "closed", "opened"}
