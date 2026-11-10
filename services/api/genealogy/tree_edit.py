"""Merging two people and removing people, safely and undoably.

Merge: one person is kept; the other's facts are brought across one by one (the user can
leave some out), their relatives, residences and tree IDs move to the kept person, and the
other record is removed. Nothing is merged automatically (ADR-005), and a merge is one
ChangeSet, so it can be undone.

Removal: before removing someone, show who would be cut off from the rest of the tree
(people only connected through them), and let the user keep or remove those too.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from history.models import Assertion, AssertionEvidence, Decision, Person

from .changes import Recorder
from .exporter import current_values
from .models import ChangeKind, ExternalId, GalleryTag, RelationKind, Relationship, Residence


class MergeRefused(Exception):
    pass


def _ct():
    return ContentType.objects.get_for_model(Person)


def _claims(person: Person):
    return Assertion.objects.filter(subject_type=_ct(), subject_id=person.id).order_by(
        "predicate", "created_at"
    )


def _display(p: Person, values: dict) -> str:
    v = values.get(p.id, {})
    return v["name"].value if "name" in v else p.name


def _relatives(person: Person) -> dict[str, set]:
    out: dict[str, set] = {"parents": set(), "children": set(), "partners": set()}
    for r in Relationship.objects.filter(person=person):
        out["children" if r.kind == RelationKind.PARENT else "partners"].add(r.relative_id)
    for r in Relationship.objects.filter(relative=person):
        out["parents" if r.kind == RelationKind.PARENT else "partners"].add(r.person_id)
    return out


def merge_preview(project, keep: Person, other: Person) -> dict[str, Any]:
    """What merging `other` into `keep` would do, question by question."""
    if keep.pk == other.pk:
        raise MergeRefused("Choose two different people.")
    kr, orr = _relatives(keep), _relatives(other)
    if other.pk in kr["parents"] | kr["children"] or keep.pk in orr["parents"] | orr["children"]:
        raise MergeRefused(
            "One of these people is recorded as the other's parent or child, so they can't be "
            "the same person. Check the relationship first."
        )
    values = current_values(project, [keep.id, other.id])
    by_q: dict[str, dict[str, list]] = defaultdict(lambda: {"keep": [], "other": []})

    def facts(p: Person, side: str) -> None:
        current = {a.pk for a in values.get(p.id, {}).values()}
        for a in _claims(p):
            by_q[a.predicate.lower()][side].append(
                {
                    "id": str(a.id),
                    "value": a.value,
                    "date_text": a.date_text,
                    "status": a.status,
                    "method": a.method,
                    "in_use": a.pk in current,
                    "evidence": a.evidence.count(),
                }
            )

    facts(keep, "keep")
    facts(other, "other")
    questions = []
    for q, sides in sorted(by_q.items()):
        kv = {f["value"].strip().lower() for f in sides["keep"] if f["in_use"]}
        ov = {f["value"].strip().lower() for f in sides["other"] if f["in_use"]}
        questions.append({
            "question": q,
            "keep": sides["keep"],
            "other": sides["other"],
            # Both have an answer in use and they differ: the user should look.
            "differs": bool(kv and ov and kv != ov),
        })  # fmt: skip
    people = {
        p.pk: p for p in Person.objects.filter(pk__in=set().union(*kr.values(), *orr.values()))
    }
    names = current_values(project, list(people))

    def described(ids) -> list[dict[str, str]]:
        return [{"id": str(i), "name": _display(people[i], names)} for i in ids if i in people]

    warnings = []
    if keep.living_status != other.living_status:
        warnings.append(
            "One is recorded as living and the other not. The kept person stays "
            f"{keep.get_living_status_display().lower()}."
        )
    if kr["parents"] and orr["parents"] and kr["parents"] != orr["parents"]:
        warnings.append("They have different parents recorded. Both sets will be kept: check them.")
    return {
        "keep": {"id": str(keep.id), "name": _display(keep, values), "living": keep.living_status},
        "other": {
            "id": str(other.id),
            "name": _display(other, values),
            "living": other.living_status,
        },
        "questions": questions,
        "relatives_moving": {
            k: described(orr[k] - kr[k] - {keep.pk}) for k in ("parents", "children", "partners")
        },
        "residences_moving": Residence.objects.filter(person=other).count(),
        "warnings": warnings,
        "note": "Facts you leave out are removed with the merged record. You can undo the merge.",
    }


@transaction.atomic
def merge(project, keep: Person, other: Person, leave_out: set[str], user):
    merge_preview(project, keep, other)  # same refusals
    rec = Recorder()
    ct = _ct()
    claims = list(_claims(other))
    dropped = [a for a in claims if str(a.id) in leave_out]
    moved = [a for a in claims if str(a.id) not in leave_out]
    # Copies first (the person before their facts), so undo can put things back in order.
    rec.before_delete(other)
    for a in dropped:
        rec.before_delete(a)
        for e in a.evidence.all():
            rec.before_delete(e)
    for a in moved:
        rec.before_change(a)
        a.subject_id = keep.id
        a.save(update_fields=["subject_id", "updated_at"])
    for d in Decision.objects.filter(subject_type=ct, subject_id=other.id):
        if Decision.objects.filter(project=d.project, subject_type=ct, subject_id=keep.id,
                                   predicate=d.predicate).exists():  # fmt: skip
            rec.before_delete(d)
            d.delete()
        else:
            rec.before_change(d)
            d.subject_id = keep.id
            d.save(update_fields=["subject_id", "updated_at"])
    links = list(
        Relationship.objects.filter(person=other) | Relationship.objects.filter(relative=other)
    )
    for r in links:
        a = keep if r.person_id == other.pk else r.person
        b = keep if r.relative_id == other.pk else r.relative
        same = Relationship.objects.filter(project=r.project, kind=r.kind)
        duplicate = (
            a.pk == b.pk
            or same.filter(person=a, relative=b).exists()
            or (r.kind == RelationKind.SPOUSE and same.filter(person=b, relative=a).exists())
        )
        if duplicate:
            rec.before_delete(r)
            r.delete()
        else:
            rec.before_change(r)
            r.person, r.relative = a, b
            r.save()
    for res in Residence.objects.filter(person=other):
        rec.before_change(res)
        res.person = keep
        res.save(update_fields=["person", "updated_at"])
    for t in GalleryTag.objects.filter(person=other):
        if GalleryTag.objects.filter(item=t.item, person=keep).exists():
            rec.before_delete(t)
            t.delete()
        else:
            rec.before_change(t)
            t.person = keep
            t.save(update_fields=["person", "updated_at"])
    for x in ExternalId.objects.filter(person=other):
        rec.before_change(x)
        x.person = keep
        x.save(update_fields=["person", "updated_at"])
    for e in AssertionEvidence.objects.filter(assertion__in=dropped):
        e.delete()
    for a in dropped:
        a.delete()
    keep_name, other_name = keep.name, other.name
    other.delete()
    n = len(dropped)
    summary = f"Merged {other_name} into {keep_name}"
    if n:
        summary += f", leaving out {n} fact{'s' if n != 1 else ''}"
    details = {"keep": str(keep.id), "other": str(other.id), "left_out": n}
    return rec.save(project, user, ChangeKind.MERGE, summary, details)


def _groups(people: set, links) -> list[set]:
    neighbours: dict[Any, set] = defaultdict(set)
    for a, b in links:
        if a in people and b in people:
            neighbours[a].add(b)
            neighbours[b].add(a)
    seen: set = set()
    out = []
    for p in people:
        if p in seen:
            continue
        stack, group = [p], set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            group.add(cur)
            stack.extend(neighbours[cur] - seen)
        out.append(group)
    return out


def delete_preview(project, person: Person) -> dict[str, Any]:
    """Who removing this person would cut off from the rest of the tree."""
    everyone = set(Person.objects.filter(project=project).values_list("pk", flat=True))
    links = list(
        Relationship.objects.filter(project=project).values_list("person_id", "relative_id")
    )
    before = _groups(everyone, links)
    home = next(g for g in before if person.pk in g)
    after = _groups(home - {person.pk}, links)
    after.sort(key=len, reverse=True)
    # The biggest piece is "the rest of the tree"; smaller pieces would be cut off.
    stranded = [g for g in after[1:]] if len(after) > 1 else []
    ids = [i for g in stranded for i in g]
    values = current_values(project, ids + [person.pk])
    people = {p.pk: p for p in Person.objects.filter(pk__in=ids)}
    return {
        "person": {"id": str(person.id), "name": _display(person, values)},
        "facts": _claims(person).count(),
        "relationships": Relationship.objects.filter(person=person).count()
        + Relationship.objects.filter(relative=person).count(),
        "residences": Residence.objects.filter(person=person).count(),
        "stranded": [
            [{"id": str(i), "name": _display(people[i], values)} for i in sorted(g, key=str)]
            for g in stranded
        ],
        "note": "People cut off are kept unless you choose to remove them too. You can undo this.",
    }


@transaction.atomic
def delete_people(project, people: list[Person], user):
    from .changes import person_bundle

    rec = Recorder()
    bundles = [person_bundle(p) for p in people]
    for bundle in bundles:  # copies first, each person before their facts
        for obj in bundle:
            rec.before_delete(obj)
    names = [p.name for p in people]
    ct = _ct()
    for p in people:
        # Facts and decisions point at a person generically, so they don't cascade:
        # remove them explicitly (their evidence goes with them).
        Decision.objects.filter(subject_type=ct, subject_id=p.id).delete()
        Assertion.objects.filter(subject_type=ct, subject_id=p.id).delete()
        p.delete()  # cascades to links, residences and tree IDs
    more = len(names) - 1
    summary = f"Removed {names[0]}" + (
        f" and {more} other{'s' if more != 1 else ''}" if more else ""
    )
    return rec.save(project, user, ChangeKind.DELETE, summary, {"people": names[:50]})
