"""Lineages (who held a role, one after another) and record orders."""

from __future__ import annotations

import re
from typing import Any, Literal
from uuid import UUID

from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from core.models import audit
from history.models import LivingStatus, Person
from projects.permissions import editable_projects, visible_projects

from .models import OrderStatus, RecordOrder
from .offers import offers, offers_for
from .succession import ROLES, lineage_subjects, succession

router = Router()
YEAR = re.compile(r"(?<![0-9])1[0-9]{3}(?![0-9])")


@router.get("/lineages")
def list_lineages(request: HttpRequest) -> list[dict[str, Any]]:
    """Places and organisations with licensees, owners, vicars and so on recorded."""
    return lineage_subjects(request.user)


@router.get("/lineages/{subject_type}/{subject_id}")
def lineage(
    request: HttpRequest, subject_type: str, subject_id: UUID, role: str = ""
) -> dict[str, Any]:
    from explorer.api import _subject

    subject = _subject(subject_type, subject_id, request.user)
    available = next(
        (s["roles"] for s in lineage_subjects(request.user) if s["id"] == str(subject_id)), []
    )
    if not role:
        if not available:
            raise HttpError(404, "Nobody is recorded in a role here yet.")
        role = available[0]["role"]
    if role not in ROLES:
        raise HttpError(422, "That isn't a role ArchiveHub follows.")
    return {**succession(request.user, subject, role), "roles": available}


# --- Record orders ----------------------------------------------------------------


def _events(person: Person) -> dict[str, dict[str, Any]]:
    from genealogy.exporter import current_values

    v = current_values(person.project, [person.id]).get(person.id, {})
    out = {}
    for event in ("birth", "death"):
        d, p = v.get(f"{event} date"), v.get(f"{event} place")
        if d or p:
            out[event] = {
                "year": (d.year_from or d.year_to) if d else None,
                "date_text": (d.date_text or d.value) if d else "",
                "place": p.value if p else "",
            }
    return out


@router.get("/projects/{project_id}/people/{person_id}/record-offers")
def record_offers(request: HttpRequest, project_id: UUID, person_id: UUID) -> dict[str, Any]:
    """Records that could be ordered for this person, with every fee shown."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    person = get_object_or_404(Person, pk=person_id, project=project)
    if person.living_status != LivingStatus.DECEASED:
        return {"events": [], "note": "Records aren't offered for people who may be living."}
    events = []
    for event, facts in _events(person).items():
        found = offers_for(event, facts["year"], facts["place"])
        events.append({"event": event, **facts, **found})
    # Marriages: from the partner links' marriage dates.
    from genealogy.models import RelationKind, Relationship

    for r in Relationship.objects.filter(
        Q(person=person) | Q(relative=person), project=project, kind=RelationKind.SPOUSE
    ):
        f = r.fields or {}
        years = YEAR.findall(f.get("marriage_date", ""))
        year = int(years[0]) if years else None
        place = f.get("marriage_place", "")
        partner = r.relative if r.person_id == person.id else r.person
        events.append(
            {
                "event": "marriage",
                "year": year,
                "date_text": f.get("marriage_date", ""),
                "place": place,
                "with": partner.name,
                **offers_for("marriage", year, place),
            }
        )
    note = (
        "ArchiveHub doesn't sell these: you order from the holder, and we keep track and "
        "file the record when it arrives."
    )
    return {"events": events, "note": note}


def _order_json(o: RecordOrder) -> dict[str, Any]:
    return {
        "id": str(o.id),
        "title": o.title,
        "holder": o.holder,
        "should_show": o.should_show,
        "route": o.route,
        "route_label": o.get_route_display(),
        "fees": o.fees,
        "total_pence": sum(f["pence"] for f in o.fees),
        "delivery": o.delivery,
        "url": o.url,
        "rights_label": o.rights_label,
        "details": o.details,
        "status": o.status,
        "status_label": o.get_status_display(),
        "reference": o.reference,
        "ordered_at": o.ordered_at,
        "received_at": o.received_at,
        "file_id": str(o.file_id) if o.file_id else None,
        "person_id": str(o.person_id) if o.person_id else None,
        "project_id": str(o.project_id) if o.project_id else None,
        "note": o.note,
    }


class OrderIn(Schema):
    project_id: UUID
    person_id: UUID
    offer_key: str
    event: Literal["birth", "marriage", "death"]
    index_reference: str = ""


@router.post("/record-orders", response={201: dict})
def plan_order(request: HttpRequest, payload: OrderIn):
    """Keep track of a record you're ordering from its holder."""
    project = get_object_or_404(editable_projects(request.user), pk=payload.project_id)
    person = get_object_or_404(Person, pk=payload.person_id, project=project)
    if person.living_status != LivingStatus.DECEASED:
        raise HttpError(422, "Records aren't offered for people who may be living.")
    offer = next((o for o in offers() if o["key"] == payload.offer_key), None)
    if offer is None or payload.event not in offer["events"]:
        raise HttpError(422, "That record can't be ordered this way.")
    if offer["needs_index_reference"] and not payload.index_reference.strip():
        raise HttpError(422, "This needs the GRO index reference. Find it in the GRO index first.")
    o = RecordOrder.objects.create(
        user=request.user, project=project, person=person, offer_key=offer["key"],
        title=f"{payload.event.capitalize()} record of {person.name}: {offer['title'].lower()}",
        holder=offer["holder"], should_show=offer["should_show"], route=offer["route"],
        fees=offer["fees"], delivery=offer["delivery"], url=offer["url"],
        rights_label=offer["rights_label"],
        details={"event": payload.event, "index_reference": payload.index_reference.strip()[:100]},
    )  # fmt: skip
    audit(request.user, "record_order.plan", o, offer=offer["key"])
    return Status(201, _order_json(o))


@router.get("/record-orders")
def list_orders(request: HttpRequest, project_id: UUID | None = None) -> list[dict[str, Any]]:
    orders = RecordOrder.objects.filter(user=request.user)
    if project_id:
        orders = orders.filter(project_id=project_id)
    return [_order_json(o) for o in orders]


class OrderUpdate(Schema):
    status: Literal["ordered", "received", "cancelled"] | None = None
    reference: str | None = None
    file_id: UUID | None = None
    note: str | None = None


NEXT = {
    OrderStatus.PLANNED: {OrderStatus.ORDERED, OrderStatus.CANCELLED},
    OrderStatus.ORDERED: {OrderStatus.RECEIVED, OrderStatus.CANCELLED},
    OrderStatus.RECEIVED: set(),
    OrderStatus.CANCELLED: set(),
}


@router.patch("/record-orders/{order_id}")
def update_order(request: HttpRequest, order_id: UUID, payload: OrderUpdate) -> dict[str, Any]:
    """Mark an order ordered, received (with the copy from your Archive) or cancelled."""
    from archive.models import FileAsset

    o = get_object_or_404(RecordOrder, pk=order_id, user=request.user)
    if payload.status and payload.status not in NEXT[o.status]:
        raise HttpError(409, f"An order that's {o.get_status_display().lower()} can't become "
                        f"{OrderStatus(payload.status).label.lower()}.")  # fmt: skip
    if payload.file_id:
        o.file = get_object_or_404(FileAsset, pk=payload.file_id, project=o.project)
    if payload.status == OrderStatus.RECEIVED and not (o.file or payload.file_id):
        raise HttpError(422, "Upload the record to your Archive and choose it first.")
    if payload.status == OrderStatus.ORDERED:
        o.ordered_at = timezone.now()
    if payload.status == OrderStatus.RECEIVED:
        o.received_at = timezone.now()
    if payload.status:
        o.status = payload.status
    if payload.reference is not None:
        o.reference = payload.reference.strip()[:100]
    if payload.note is not None:
        o.note = payload.note.strip()[:2000]
    o.save()
    return _order_json(o)
