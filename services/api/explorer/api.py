"""Archive Explorer, Research Basket and evidence decisions."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from connectors.base import ConnectorError, NotFound
from connectors.sources import CONNECTORS, get_connector
from core.models import audit
from history import queries
from history.models import Decision, Organisation, Person, Place
from projects.permissions import editable_projects, visible_projects

from .models import BasketItem

router = Router()

SUBJECT_MODELS = {"organisation": Organisation, "place": Place, "person": Person}


def _connector_or_404(key: str):
    try:
        return get_connector(key)
    except NotFound as exc:
        raise HttpError(404, "No such source.") from exc


def _connector_error(exc: ConnectorError) -> HttpError:
    status = {"not_found": 404, "bad_query": 422, "rate_limited": 429}.get(exc.kind, 503)
    return HttpError(status, exc.user_message)


# --- Explorer ----------------------------------------------------------------------


@router.get("/explorer/sources")
def explorer_sources(request: HttpRequest) -> list[dict[str, Any]]:
    out = []
    for c in CONNECTORS.values():
        info = c.describe()
        try:
            if hasattr(c, "dataset"):
                ds = c.dataset()
                info["note"] = f"{ds.row_count:,} records ({ds.import_scope})"
            info["available"] = True
        except ConnectorError as exc:
            info["available"], info["note"] = False, exc.user_message
        out.append(info)
    return out


@router.get("/explorer/{key}/search")
def explorer_search(
    request: HttpRequest, key: str, q: str = "", cursor: str | None = None, page_size: int = 25
) -> dict[str, Any]:
    connector = _connector_or_404(key)
    try:
        page = connector.search(q[:200], cursor=cursor, page_size=page_size)
    except ConnectorError as exc:
        raise _connector_error(exc) from exc
    return {
        "records": [r.to_dict() for r in page.records],
        "next_cursor": page.next_cursor,
        "searched": page.searched,
    }


@router.get("/explorer/{key}/records/{record_id}")
def explorer_record(request: HttpRequest, key: str, record_id: str) -> dict[str, Any]:
    connector = _connector_or_404(key)
    try:
        record = connector.get_record(record_id)
    except ConnectorError as exc:
        raise _connector_error(exc) from exc
    data = record.to_dict()
    data["citation"] = connector.citation(record)
    data["storage"] = connector.storage_policy(record)
    data["source_name"] = connector.name
    return data


# --- Research Basket ---------------------------------------------------------------


class BasketIn(Schema):
    connector: str
    record_id: str
    note: str = ""


class BasketOut(Schema):
    id: UUID
    connector: str
    external_id: str
    title: str
    url: str
    storage: str
    note: str
    created_at: datetime


@router.get("/projects/{project_id}/basket", response=list[BasketOut])
def list_basket(request: HttpRequest, project_id: UUID):
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    return BasketItem.objects.filter(project=project)


@router.post("/projects/{project_id}/basket", response={201: BasketOut, 200: BasketOut})
def add_to_basket(request: HttpRequest, project_id: UUID, payload: BasketIn):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    connector = _connector_or_404(payload.connector)
    try:
        record = connector.get_record(payload.record_id)
    except ConnectorError as exc:
        raise _connector_error(exc) from exc
    storage = connector.storage_policy(record)
    item, created = BasketItem.objects.get_or_create(
        project=project,
        connector=connector.key,
        external_id=record.id,
        defaults={
            "title": record.title[:400],
            "url": record.url,
            "storage": storage,
            # Keep a copy only where the source's terms allow it.
            "snapshot": record.to_dict() if storage == "full_copy" else None,
            "note": payload.note[:2000],
            "added_by": request.user,
        },
    )
    if created:
        audit(request.user, "basket.add", item, connector=connector.key)
    return Status(201 if created else 200, item)


@router.delete("/projects/{project_id}/basket/{item_id}", response={204: None})
def remove_from_basket(request: HttpRequest, project_id: UUID, item_id: UUID):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    item = get_object_or_404(BasketItem, pk=item_id, project=project)
    audit(request.user, "basket.remove", item, title=item.title)
    item.delete()
    return Status(204, None)


# --- Evidence and decisions --------------------------------------------------------


def _subject(subject_type: str, subject_id: UUID):
    model = SUBJECT_MODELS.get(subject_type)
    if model is None:
        raise HttpError(422, "Unknown subject type.")
    return get_object_or_404(model, pk=subject_id)


@router.get("/evidence/{subject_type}/{subject_id}")
def evidence(
    request: HttpRequest,
    subject_type: str,
    subject_id: UUID,
    predicate: str,
    project_id: UUID | None = None,
) -> dict[str, Any]:
    """Every claim on one question, with evidence, plus the project's decision if any."""
    subject = _subject(subject_type, subject_id)
    claims = queries.claims_about(request.user, subject, predicate).get(predicate, [])
    if not claims:
        # Predicates are matched case-insensitively; fall back to the stored spelling.
        grouped = queries.claims_about(request.user, subject, predicate)
        claims = next(iter(grouped.values()), [])
    decision = None
    if project_id:
        project = get_object_or_404(visible_projects(request.user), pk=project_id)
        d = Decision.objects.filter(
            project=project,
            subject_type=ContentType.objects.get_for_model(subject),
            subject_id=subject.pk,
            predicate__iexact=predicate,
        ).first()
        if d:
            decision = {
                "chosen_id": str(d.chosen_id) if d.chosen_id else None,
                "keep_disputed": d.keep_disputed,
                "reason": d.reason,
                "decided_at": d.updated_at.isoformat(),
            }
    return {
        "subject": {"type": subject_type, "id": str(subject.pk), "name": subject.name},
        "predicate": predicate,
        "disputed": queries.is_disputed(claims) if claims else False,
        "claims": [
            {
                "id": str(c.id),
                "value": c.value,
                "date": c.date_display or None,
                "status": c.status,
                "method": c.method,
                "note": c.note,
                "evidence": [
                    {
                        "record_title": e.record.title,
                        "record_key": e.record.key,
                        "source": e.record.source.name,
                        "url": e.record.url,
                        "what_it_says": e.note,
                        "stance": e.stance,
                        "suggested_weight": e.suggested_weight or None,
                        "weight_suggested_by": e.weight_by or None,
                    }
                    for e in c.evidence.all()
                ],
            }
            for c in claims
        ],
        "decision": decision,
    }


class DecisionIn(Schema):
    subject_type: str
    subject_id: UUID
    predicate: str
    chosen_id: UUID | None = None
    keep_disputed: bool = False
    reason: str = ""


@router.put("/projects/{project_id}/decisions")
def save_decision(request: HttpRequest, project_id: UUID, payload: DecisionIn) -> dict[str, Any]:
    """Record what this project uses. 'Use' doesn't mean 'true'; nothing is deleted."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    subject = _subject(payload.subject_type, payload.subject_id)
    if bool(payload.chosen_id) == payload.keep_disputed:
        raise HttpError(422, "Choose one answer, or keep it disputed.")
    chosen = None
    if payload.chosen_id:
        chosen = get_object_or_404(
            queries.visible_assertions(request.user),
            pk=payload.chosen_id,
            subject_id=subject.pk,
            predicate__iexact=payload.predicate,
        )
    ct = ContentType.objects.get_for_model(subject)
    decision, _ = Decision.objects.update_or_create(
        project=project,
        subject_type=ct,
        subject_id=subject.pk,
        predicate=chosen.predicate if chosen else payload.predicate,
        defaults={
            "chosen": chosen,
            "keep_disputed": payload.keep_disputed,
            "reason": payload.reason[:2000],
            "decided_by": request.user,
        },
    )
    audit(
        request.user,
        "decision.save",
        decision,
        predicate=decision.predicate,
        chosen=str(chosen.id) if chosen else None,
    )
    return {"ok": True, "chosen_id": str(chosen.id) if chosen else None}
