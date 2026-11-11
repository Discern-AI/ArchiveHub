"""Culture items and Life Reports."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from core.models import audit
from history.models import LivingStatus, Person
from projects.permissions import editable_projects, visible_projects

from .models import CultureItem, ItemStatus, LifeReport
from .report import build_report, item_block

router = Router()


@router.get("/culture/items")
def culture_items(request: HttpRequest, q: str = "") -> list[dict[str, Any]]:
    """Approved culture items, with their rights."""
    items = CultureItem.objects.filter(status=ItemStatus.APPROVED)
    if q.strip():
        items = items.filter(title__icontains=q.strip())
    return [item_block(i, []) for i in items[:100]]


@router.get("/projects/{project_id}/people/{person_id}/life-report")
def draft_report(
    request: HttpRequest,
    project_id: UUID,
    person_id: UUID,
    length: Literal["short", "long"] = "short",
) -> dict[str, Any]:
    """A draft Life Report to read and edit. Nothing is saved or published."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    person = get_object_or_404(Person, pk=person_id, project=project)
    return build_report(project, person, length)


class SaveIn(Schema):
    length: Literal["short", "long"] = "short"
    blocks: list[dict[str, Any]]


TEXT_TYPES = {"title", "heading", "paragraph", "context", "gaps", "glance"}


@router.post("/projects/{project_id}/people/{person_id}/life-reports", response={201: dict})
def save_report(request: HttpRequest, project_id: UUID, person_id: UUID, payload: SaveIn):
    """Save the report as edited. Culture items are re-read from the approved record, so
    an image or credit can't be changed and nothing unapproved can be added."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    person = get_object_or_404(Person, pk=person_id, project=project)
    if person.living_status != LivingStatus.DECEASED:
        raise HttpError(422, "Life Reports are only written for people who have died.")
    blocks, keys = [], []
    for b in payload.blocks[:200]:
        kind = b.get("type")
        if kind == "culture":
            item = CultureItem.objects.filter(key=b.get("key"), status=ItemStatus.APPROVED).first()
            if item is None:
                raise HttpError(422, "That culture item isn't approved for use.")
            why = str(b.get("why", ""))[:1000]
            blocks.append(item_block(item, [why] if why else []))
            keys.append(item.key)
        elif kind in TEXT_TYPES:
            blocks.append({k: v for k, v in b.items() if isinstance(v, str | int | list | None)})
        else:
            raise HttpError(422, "The report has a part that isn't recognised.")
    report = LifeReport.objects.create(
        project=project,
        person=person,
        length=payload.length,
        blocks=blocks,
        items=keys,
        created_by=request.user,
    )
    audit(request.user, "life_report.save", report, person=str(person.id))
    return Status(201, {"id": str(report.id), "created_at": report.created_at, "items": keys})


@router.get("/projects/{project_id}/people/{person_id}/life-reports")
def list_reports(request: HttpRequest, project_id: UUID, person_id: UUID) -> list[dict[str, Any]]:
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    reports = LifeReport.objects.filter(project=project, person_id=person_id)
    return [{"id": str(r.id), "created_at": r.created_at, "length": r.length,
             "blocks": r.blocks, "items": r.items} for r in reports]  # fmt: skip
