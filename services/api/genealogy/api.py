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
from history.models import Assertion, AssertionEvidence, LivingStatus, Method, Person
from projects.permissions import editable_projects, visible_projects

from .exporter import current_values, export_gedcom, export_gedzip
from .health import check_tree
from .lifeline import lifeline
from .models import OverlayEvent, OverlayKind, OverlayPreset, RelationKind, Relationship
from .record_guide import record_office_for, where_to_look

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
                            {
                                "title": e.title,
                                "url": e.url,
                                "what_it_says": e.note,
                                "source": e.source_name,
                                "stance": e.stance,
                            }
                            for e in c.evidence.all()
                        ],  # fmt: skip
                    }
                    for c in claims
                ],
            }
            for predicate, claims in grouped.items()
        ],
    }


class EvidenceIn(Schema):
    basket_item_id: UUID
    note: str = ""
    stance: Literal["supports", "disputes", "mentions"] = "supports"


class CorrectionIn(Schema):
    predicate: str
    value: str
    status: Literal["documented", "remembered", "inferred"] = "remembered"
    note: str = ""
    evidence: list[EvidenceIn] = []


def _attach(project, claim: Assertion, items: list[EvidenceIn], user) -> int:
    """Attach saved Research Basket items from the same project as evidence."""
    from explorer.models import BasketItem

    added = 0
    for item in items:
        saved = BasketItem.objects.filter(project=project, pk=item.basket_item_id).first()
        if saved is None:
            raise HttpError(422, "That saved item isn't in this project's Research Basket.")
        _, created = AssertionEvidence.objects.get_or_create(
            assertion=claim,
            basket_item=saved,
            defaults={"note": item.note.strip()[:2000], "stance": item.stance},
        )
        if created:
            added += 1
            audit(user, "evidence.add", claim, basket_item=str(saved.id))
    return added


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
    _attach(project, a, payload.evidence, request.user)
    return Status(201, {"id": str(a.id)})


@router.post("/projects/{project_id}/claims/{claim_id}/evidence", response={201: dict})
def add_evidence(request: HttpRequest, project_id: UUID, claim_id: UUID, payload: EvidenceIn):
    """Back an existing fact with something saved to the Research Basket."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    claim = get_object_or_404(Assertion, pk=claim_id, project=project)
    added = _attach(project, claim, [payload], request.user)
    return Status(201, {"added": added})


@router.get("/projects/{project_id}/people/{person_id}/where-to-look")
def where_to_look_for(request: HttpRequest, project_id: UUID, person_id: UUID) -> dict[str, Any]:
    """Records that could exist for this person, who holds them and what they cost."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    person = get_object_or_404(Person, pk=person_id, project=project)
    if person.living_status != LivingStatus.DECEASED:
        return {
            "steps": [],
            "note": "This person may be living, so no record search is suggested.",
        }
    v = current_values(project, [person.id]).get(person.id, {})
    facts: dict[str, dict[str, Any]] = {}
    for event in ("birth", "baptism", "death", "burial"):
        d, p = v.get(f"{event} date"), v.get(f"{event} place")
        year = (d.year_from or d.year_to) if d else None
        if year or p:
            facts[event] = {"year": year, "place": p.value if p else ""}
    places = " ".join(f["place"] for f in facts.values())
    steps = where_to_look(facts, record_office_for(places), person.sex)
    return {
        "steps": [s.to_dict() for s in steps],
        "note": "Where records would be if they exist; a search may find nothing. "
        "Routes marked as leads haven't been checked against official guidance yet.",
    }


@router.get("/projects/{project_id}/tree-graph")
def tree_graph(request: HttpRequest, project_id: UUID) -> dict[str, Any]:
    """Everyone in the tree with the links between them, for drawing the chart."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    people = list(Person.objects.filter(project=project))
    values = current_values(project, [p.id for p in people])

    def year(v, *labels):
        for label in labels:
            a = v.get(f"{label} date")
            if a is not None and (a.year_from or a.year_to):
                return a.year_from or a.year_to
        return None

    nodes = []
    for p in people:
        v = values.get(p.id, {})
        living = p.living_status != LivingStatus.DECEASED
        nodes.append(
            {
                "id": str(p.id),
                "name": v["name"].value if "name" in v else p.name,
                "sex": p.sex,
                "living": living,
                # Living people's dates stay off the chart, as on the family page.
                "born": None if living else year(v, "birth", "baptism"),
                "died": None if living else year(v, "death", "burial"),
            }
        )
    links = [
        {"from": str(r.person_id), "to": str(r.relative_id), "kind": r.kind}
        for r in Relationship.objects.filter(project=project)
    ]
    return {"people": nodes, "links": links}


@router.get("/projects/{project_id}/tree-health")
def tree_health(request: HttpRequest, project_id: UUID) -> dict[str, Any]:
    """Things in the tree worth a second look. Nothing is changed."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    return check_tree(project)


@router.get("/projects/{project_id}/gedcom", response=None)
def download_gedcom(
    request: HttpRequest, project_id: UUID, version: Literal["5.5.1", "7.0"] = "5.5.1"
) -> HttpResponse:
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    if not Person.objects.filter(project=project).exists():
        raise HttpError(404, "This project has no family tree to export.")
    response = HttpResponse(
        export_gedcom(project, version), content_type="text/plain; charset=utf-8"
    )
    safe = "".join(ch for ch in project.title if ch.isalnum() or ch in " -_")[:60] or "family"
    response["Content-Disposition"] = f'attachment; filename="{safe.strip()}.ged"'
    audit(request.user, "gedcom.export", project, version=version)
    return response


@router.get("/projects/{project_id}/gedzip", response=None)
def download_gedzip(request: HttpRequest, project_id: UUID) -> HttpResponse:
    """GEDCOM 7 with the evidence files for people who have died, in one .gdz file."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    if not Person.objects.filter(project=project).exists():
        raise HttpError(404, "This project has no family tree to export.")
    data, count = export_gedzip(project)
    response = HttpResponse(data, content_type="application/zip")
    safe = "".join(ch for ch in project.title if ch.isalnum() or ch in " -_")[:60] or "family"
    response["Content-Disposition"] = f'attachment; filename="{safe.strip()}.gdz"'
    audit(request.user, "gedcom.export", project, version="gedzip", files=count)
    return response


# --- Lifeline ---------------------------------------------------------------------


@router.get("/projects/{project_id}/lifeline")
def lifeline_view(request: HttpRequest, project_id: UUID) -> dict[str, Any]:
    """Everyone as a span through time, their recorded places and the overlays."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    return lifeline(project, request.user)


class MarkerIn(Schema):
    title: str
    year_from: int
    year_to: int | None = None
    note: str = ""


def _marker(o: OverlayEvent) -> dict[str, Any]:
    return {"id": str(o.id), "kind": o.kind, "title": o.title, "year_from": o.year_from,
            "year_to": o.year_to, "date_text": o.date_text, "area": o.area, "note": o.note,
            "source_title": "", "source_url": "", "builtin": False}  # fmt: skip


@router.post("/projects/{project_id}/lifeline/markers", response={201: dict})
def add_marker(request: HttpRequest, project_id: UUID, payload: MarkerIn):
    """A marker of your own on the Lifeline, such as the year you were born."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    title = payload.title.strip()[:200]
    end = payload.year_to
    if not title:
        raise HttpError(422, "Give the marker a name.")
    if not (1 <= payload.year_from <= 2200) or (end is not None and end < payload.year_from):
        raise HttpError(422, "Those years don't make sense.")
    o = OverlayEvent.objects.create(
        project=project, kind=OverlayKind.CUSTOM, title=title, year_from=payload.year_from,
        year_to=end, note=payload.note.strip()[:1000], created_by=request.user,
    )  # fmt: skip
    return Status(201, _marker(o))


@router.delete("/projects/{project_id}/lifeline/markers/{marker_id}", response={204: None})
def delete_marker(request: HttpRequest, project_id: UUID, marker_id: UUID):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    get_object_or_404(OverlayEvent, pk=marker_id, project=project).delete()
    return Status(204, None)


class PresetIn(Schema):
    kinds: list[str]


@router.put("/projects/{project_id}/lifeline/preset")
def save_preset(request: HttpRequest, project_id: UUID, payload: PresetIn) -> dict[str, Any]:
    """Which layers you have switched on, remembered per project."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    allowed = {k.value for k in OverlayKind} | {"family"}
    kinds = [k for k in dict.fromkeys(payload.kinds) if k in allowed]
    OverlayPreset.objects.update_or_create(
        project=project, user=request.user, defaults={"kinds": kinds}
    )
    return {"kinds": kinds}
