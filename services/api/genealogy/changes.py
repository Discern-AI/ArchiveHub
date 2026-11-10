"""Undoable changes to a tree.

A Recorder notes everything a bulk change creates, alters (with a copy of what was there
before) and removes (with a full copy). Saved as a ChangeSet, it can be undone in one
step. Undo refuses, and says why, when something later depends on the change: a later
change set touching the same things, or the user's own additions to people it created.
"""

from __future__ import annotations

import json
from typing import Any

from django.apps import apps
from django.core import serializers
from django.db import transaction
from django.db.models import Model
from django.utils import timezone

from history.models import Assertion, AssertionEvidence, Decision, Person

from .models import ChangeSet, ExternalId, GalleryTag, Relationship, Residence


def _label(obj: Model) -> str:
    return obj._meta.label_lower


def snapshot(obj: Model) -> dict[str, Any]:
    """A full copy of a row that can be stored as JSON and put back exactly."""
    return json.loads(serializers.serialize("json", [obj]))[0]


def _restore(copy: dict[str, Any]) -> int:
    n = 0
    for obj in serializers.deserialize("json", json.dumps([copy])):
        obj.save()
        n += 1
    return n


class Recorder:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        self._seen: set[tuple[str, str]] = set()

    def created(self, obj: Model) -> None:
        key = (_label(obj), str(obj.pk))
        if key not in self._seen:
            self._seen.add(key)
            self.items.append({"action": "created", "model": key[0], "pk": key[1]})

    def before_change(self, obj: Model) -> None:
        """Call before altering an object that existed before this change."""
        key = (_label(obj), str(obj.pk))
        if key not in self._seen:
            self._seen.add(key)
            self.items.append(
                {"action": "updated", "model": key[0], "pk": key[1], "before": snapshot(obj)}
            )

    def before_delete(self, obj: Model) -> None:
        key = (_label(obj), str(obj.pk))
        if key in self._seen and any(
            i["action"] == "created" and (i["model"], i["pk"]) == key for i in self.items
        ):
            # Made and removed in the same change: nothing to restore.
            self.items = [i for i in self.items if (i["model"], i["pk"]) != key]
            return
        if key in self._seen:
            return  # already copied (e.g. a link between two people being removed)
        self._seen.add(key)
        self.items.append(
            {"action": "deleted", "model": key[0], "pk": key[1], "before": snapshot(obj)}
        )

    def touched(self) -> set[tuple[str, str]]:
        return {(i["model"], i["pk"]) for i in self.items}

    def save(self, project, user, kind: str, summary: str, details: dict) -> ChangeSet:
        return ChangeSet.objects.create(
            project=project, user=user, kind=kind, summary=summary[:300], details=details,
            items=self.items,
        )  # fmt: skip


def person_bundle(person: Person) -> list[Model]:
    """A person and everything that belongs to them, parents before children, so a copy
    can be put back in this order."""
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(Person)
    claims = list(Assertion.objects.filter(subject_type=ct, subject_id=person.id))
    evidence = list(AssertionEvidence.objects.filter(assertion__in=claims))
    links = list(
        Relationship.objects.filter(person=person) | Relationship.objects.filter(relative=person)
    )
    return [
        person,
        *claims,
        *evidence,
        *links,
        *Residence.objects.filter(person=person),
        *ExternalId.objects.filter(person=person),
        *Decision.objects.filter(subject_type=ct, subject_id=person.id),
        *GalleryTag.objects.filter(person=person),
    ]


def _touched(cs: ChangeSet) -> set[tuple[str, str]]:
    return {(i["model"], i["pk"]) for i in cs.items}


def blockers(cs: ChangeSet) -> list[str]:
    """Reasons this change can't be undone yet. Empty if it can."""
    reasons = []
    mine = _touched(cs)
    later = ChangeSet.objects.filter(
        project=cs.project, created_at__gt=cs.created_at, undone_at__isnull=True
    )
    for other in later:
        if mine & _touched(other):
            reasons.append(f"Undo the later change first: {other.summary}")
    created_people = [
        i["pk"] for i in cs.items if i["action"] == "created" and i["model"] == "history.person"
    ]
    if created_people:
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(Person)
        own = (
            Assertion.objects.filter(subject_type=ct, subject_id__in=created_people)
            .exclude(pk__in=[i["pk"] for i in cs.items if i["model"] == "history.assertion"])
            .count()
        )
        if own:
            reasons.append(
                f"{own} fact{'s' if own != 1 else ''} added since to people this change "
                "brought in would be lost. Remove them first."
            )
    return reasons


@transaction.atomic
def undo(cs: ChangeSet, user) -> dict[str, int]:
    if cs.undone_at:
        raise ValueError("This change has already been undone.")
    counts = {"removed": 0, "restored": 0, "put_back": 0}
    # 1. Remove what it created, newest first (children before parents).
    for item in reversed(cs.items):
        if item["action"] != "created":
            continue
        model = apps.get_model(item["model"])
        deleted, _ = model.objects.filter(pk=item["pk"]).delete()
        counts["removed"] += 1 if deleted else 0
    # 2. Put back what it removed, in the order it was copied (parents first).
    for item in cs.items:
        if item["action"] == "deleted":
            counts["put_back"] += _restore(item["before"])
    # 3. Restore what it changed to how it was.
    for item in cs.items:
        if item["action"] == "updated":
            counts["restored"] += _restore(item["before"])
    cs.undone_at = timezone.now()
    cs.undone_by = user
    cs.save(update_fields=["undone_at", "undone_by", "updated_at"])
    return counts
