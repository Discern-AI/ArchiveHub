"""Family: people in a project, their claims with evidence, corrections and export."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from core.models import audit
from history import queries
from history.models import Assertion, Method, Person
from projects.permissions import editable_projects, visible_projects

from .exporter import current_values, export_gedcom
from .models import RelationKind, Relationship

router = Router()
SUMMARY = ("birth date", "birth place", "death date", "death place")


def _brief(p: Person, values: dict) -> dict[str, Any]:
    v = values.get(p.id, {})
    return {
        "id": str(p.id),
        "name": v["name"].value if "name" in v else p.name,
        "living": p.living_status == "living",
        "birth": " ".join(x for x in [v.get("birth date") and v["birth date"].value,
                                     v.get("birth place") and v["birth place"].value] if x),
        "death": " ".join(x for x in [v.get("death date") and v["death date"].value,
                                     v.get("death place") and v["death place"].value] if x),
    }  # fmt: skip


@router.get("/projects/{project_id}/people")
def list_people(request: HttpRequest, project_id: UUID, q: str = "") -> list[dict[str, Any]]:
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    people = Person.objects.filter(project=project).order_by("name")
    if q.strip():
        people = people.filter(name__icontains=q.strip())
    people = list(people[:500])
    values = current_values(project, [p.id for p in people])
    return [_brief(p, values) for p in people]


@router.get("/projects/{project_id}/people/{person_id}")
def person_detail(request: HttpRequest, project_id: UUID, person_id: UUID) -> dict[str, Any]:
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    person = get_object_or_404(Person, pk=person_id, project=project)
    grouped = queries.claims_about(request.user, person)
    values = current_values(project, [person.id])
    links = Relationship.objects.filter(project=project).filter(
        Q(person=person) | Q(relative=person)
    )
    parents, children, partners = [], [], []
    for r in links.select_related("person", "relative"):
        if r.kind == RelationKind.PARENT and r.relative_id == person.id:
            parents.append(r.person)
        elif r.kind == RelationKind.PARENT:
            children.append(r.relative)
        else:
            partners.append(r.relative if r.person_id == person.id else r.person)
    rel_values = current_values(project, [p.id for p in parents + children + partners])
    chosen = {k: a.id for k, a in values.get(person.id, {}).items()}
    return {
        **_brief(person, values),
        "parents": [_brief(p, rel_values) for p in parents],
        "partners": [_brief(p, rel_values) for p in partners],
        "children": [_brief(p, rel_values) for p in children],
        "facts": [
            {
                "question": predicate,
                "disputed": queries.is_disputed(claims) or len({c.value for c in claims}) > 1,
                "answers": [
                    {
                        "id": str(c.id),
                        "value": c.value,
                        "status": c.status,
                        "method": c.method,
                        "note": c.note,
                        "in_use": chosen.get(predicate.lower()) == c.id,
                        "evidence": [
                            {"title": e.title, "url": e.url, "what_it_says": e.note}
                            for e in c.evidence.all()
                        ],  # fmt: skip
                    }
                    for c in claims
                ],
            }
            for predicate, claims in grouped.items()
        ],
    }


class CorrectionIn(Schema):
    predicate: str
    value: str
    status: Literal["documented", "remembered", "inferred"] = "remembered"
    note: str = ""


@router.post("/projects/{project_id}/people/{person_id}/claims", response={201: dict})
def add_claim(request: HttpRequest, project_id: UUID, person_id: UUID, payload: CorrectionIn):
    """Add or correct a fact. The imported claim stays; this one sits beside it."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    person = get_object_or_404(Person, pk=person_id, project=project)
    predicate = payload.predicate.strip().lower()[:60]
    value = payload.value.strip()[:1000]
    if not predicate or not value:
        raise HttpError(422, "Say what you're correcting and the new value.")
    a = Assertion.objects.create(
        subject_type=ContentType.objects.get_for_model(Person),
        subject_id=person.id,
        predicate=predicate,
        value=value,
        status=payload.status,
        method=Method.USER,
        project=project,
        created_by=request.user,
        note=payload.note.strip()[:2000],
    )
    audit(request.user, "claim.add", a, predicate=predicate)
    return Status(201, {"id": str(a.id)})


@router.get("/projects/{project_id}/gedcom", response=None)
def download_gedcom(request: HttpRequest, project_id: UUID) -> HttpResponse:
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    if not Person.objects.filter(project=project).exists():
        raise HttpError(404, "This project has no family tree to export.")
    response = HttpResponse(export_gedcom(project), content_type="text/plain; charset=utf-8")
    safe = "".join(ch for ch in project.title if ch.isalnum() or ch in " -_")[:60] or "family"
    response["Content-Disposition"] = f'attachment; filename="{safe.strip()}.ged"'
    audit(request.user, "gedcom.export", project)
    return response
