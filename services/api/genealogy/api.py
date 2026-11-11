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

from .changes import blockers, undo
from .context import life_and_times
from .explain import explain_record
from .exporter import current_values, export_gedcom, export_gedzip
from .gallery import (
    family_gallery,
    person_gallery,
    reorder,
    suggest_people,
    unplaced_images,
    year_of,
)
from .gallery import item_json as gallery_item_json
from .health import check_tree
from .life_story import life_story
from .lifeline import lifeline
from .models import (
    ChangeSet,
    Explanation,
    ExternalId,
    GalleryItem,
    GalleryTag,
    OverlayEvent,
    OverlayKind,
    OverlayPreset,
    RelationKind,
    Relationship,
)
from .record_guide import record_office_for, where_to_look
from .tree_edit import MergeRefused, delete_people, delete_preview, merge, merge_preview

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


# --- Imports, tree versions and undo ----------------------------------------------


@router.get("/files/{file_id}/gedcom-preview")
def gedcom_preview(
    request: HttpRequest, file_id: UUID, mode: Literal["new", "update"] = "new", base: str = ""
) -> dict[str, Any]:
    """What importing this file would add, update and find wrong. Nothing is saved."""
    from archive.models import FileAsset
    from archive.processing import JobFailed

    from .importer import preview

    f = get_object_or_404(
        FileAsset.objects.filter(project__in=editable_projects(request.user)), pk=file_id
    )
    try:
        return preview(f, request.user, mode=mode, base=base)
    except JobFailed as exc:
        raise HttpError(422, str(exc)) from exc


@router.get("/projects/{project_id}/trees")
def imported_trees(request: HttpRequest, project_id: UUID) -> list[dict[str, Any]]:
    """Family trees imported into this project, so a new export can update one."""
    from django.db.models import Count

    from archive.models import FileAsset

    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    rows = (
        ExternalId.objects.filter(project=project)
        .values("system")
        .annotate(people=Count("id"))
        .order_by("system")
    )
    out = []
    for row in rows:
        file_id = row["system"].removeprefix("gedcom:")
        first = FileAsset.objects.filter(pk=file_id).first() if len(file_id) == 36 else None
        updates = ChangeSet.objects.filter(
            project=project, details__tree=row["system"], undone_at__isnull=True
        ).order_by("-created_at")
        latest = updates.first()
        out.append(
            {
                "tree": row["system"],
                "first_file": first.name if first else "An earlier import",
                "people": row["people"],
                "last_updated": latest.created_at if latest else None,
                "last_file": latest.details.get("file_name", "") if latest else "",
            }
        )
    return out


def _change_json(cs: ChangeSet) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for i in cs.items:
        counts[i["action"]] = counts.get(i["action"], 0) + 1
    return {
        "id": str(cs.id),
        "kind": cs.kind,
        "summary": cs.summary,
        "created_at": cs.created_at,
        "by": str(cs.user) if cs.user else "",
        "undone_at": cs.undone_at,
        "counts": counts,
        "blocked": [] if cs.undone_at else blockers(cs),
    }


@router.get("/projects/{project_id}/changes")
def list_changes(request: HttpRequest, project_id: UUID) -> list[dict[str, Any]]:
    """Bulk changes to this tree, newest first, each with whether it can be undone."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    return [_change_json(cs) for cs in ChangeSet.objects.filter(project=project)[:50]]


@router.post("/projects/{project_id}/changes/{change_id}/undo")
def undo_change(request: HttpRequest, project_id: UUID, change_id: UUID) -> dict[str, Any]:
    """Undo a whole import, update, merge or deletion in one step."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    cs = get_object_or_404(ChangeSet, pk=change_id, project=project)
    if cs.undone_at:
        raise HttpError(409, "This change has already been undone.")
    reasons = blockers(cs)
    if reasons:
        raise HttpError(409, " ".join(reasons))
    counts = undo(cs, request.user)
    audit(request.user, "tree.undo", project, change=str(cs.id), kind=cs.kind)
    return {**_change_json(cs), "result": counts}


# --- Merging and removing people ---------------------------------------------------


def _tree_person(project, person_id):
    return get_object_or_404(Person, pk=person_id, project=project)


@router.get("/projects/{project_id}/people/{person_id}/merge-preview")
def merge_preview_view(
    request: HttpRequest, project_id: UUID, person_id: UUID, other: UUID
) -> dict[str, Any]:
    """What merging another person into this one would do. Nothing is changed."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    try:
        return merge_preview(
            project, _tree_person(project, person_id), _tree_person(project, other)
        )
    except MergeRefused as exc:
        raise HttpError(422, str(exc)) from exc


class MergeIn(Schema):
    other: UUID
    leave_out: list[UUID] = []


@router.post("/projects/{project_id}/people/{person_id}/merge")
def merge_view(request: HttpRequest, project_id: UUID, person_id: UUID, payload: MergeIn):
    """Merge another person into this one, leaving out the facts the user chose."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    keep = _tree_person(project, person_id)
    try:
        cs = merge(project, keep, _tree_person(project, payload.other),
                   {str(i) for i in payload.leave_out}, request.user)  # fmt: skip
    except MergeRefused as exc:
        raise HttpError(422, str(exc)) from exc
    audit(request.user, "tree.merge", project, keep=str(keep.id), other=str(payload.other))
    return {"change_set": str(cs.id), "summary": cs.summary, "person": str(keep.id)}


@router.get("/projects/{project_id}/people/{person_id}/delete-preview")
def delete_preview_view(request: HttpRequest, project_id: UUID, person_id: UUID):
    """What removing this person would take with it, and who would be cut off."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    return delete_preview(project, _tree_person(project, person_id))


class DeleteIn(Schema):
    # People cut off by the removal that the user also wants removed.
    also: list[UUID] = []


@router.post("/projects/{project_id}/people/{person_id}/delete")
def delete_view(request: HttpRequest, project_id: UUID, person_id: UUID, payload: DeleteIn):
    """Remove a person (and any cut-off people chosen), undoably."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    person = _tree_person(project, person_id)
    allowed = {p["id"] for group in delete_preview(project, person)["stranded"] for p in group}
    extra = [str(i) for i in payload.also]
    if any(i not in allowed for i in extra):
        raise HttpError(422, "Only people cut off by this removal can be removed with it.")
    people = [person, *Person.objects.filter(project=project, pk__in=extra)]
    cs = delete_people(project, people, request.user)
    audit(request.user, "tree.delete", project, people=len(people))
    return {"change_set": str(cs.id), "summary": cs.summary}


# --- Life Story and galleries -------------------------------------------------------


@router.get("/projects/{project_id}/people/{person_id}/life-story")
def life_story_view(request: HttpRequest, project_id: UUID, person_id: UUID) -> dict[str, Any]:
    """The person's life in order, from the tree's own facts, with sources and gaps."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    return life_story(project, _tree_person(project, person_id))


@router.get("/projects/{project_id}/people/{person_id}/gallery")
def person_gallery_view(
    request: HttpRequest, project_id: UUID, person_id: UUID
) -> list[dict[str, Any]]:
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    return person_gallery(project, _tree_person(project, person_id))


@router.get("/projects/{project_id}/gallery")
def family_gallery_view(request: HttpRequest, project_id: UUID) -> list[dict[str, Any]]:
    """Every picture in the family's galleries, oldest first."""
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    return family_gallery(project)


class TagIn(Schema):
    person_id: UUID
    relation: Literal["shows", "about", "context"] = "shows"


class GalleryIn(Schema):
    file_id: UUID
    caption: str = ""
    date_text: str = ""
    place_text: str = ""
    tags: list[TagIn] = []


def _item_out(project, item: GalleryItem) -> dict[str, Any]:
    people = list(Person.objects.filter(pk__in=item.tags.values("person_id")))
    names = {p.id: p.name for p in people}
    return gallery_item_json(item, names)


@router.post("/projects/{project_id}/gallery", response={201: dict})
def add_to_gallery(request: HttpRequest, project_id: UUID, payload: GalleryIn):
    """Put a picture from the Archive into galleries, tagged to people. Adding the same
    picture again adds the new tags to it."""
    from archive.models import FileAsset, FileKind

    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    f = get_object_or_404(FileAsset, pk=payload.file_id, project=project)
    if f.kind not in (FileKind.IMAGE, FileKind.PDF):
        raise HttpError(422, "Only pictures and scanned documents can go in a gallery.")
    item, _ = GalleryItem.objects.get_or_create(
        project=project, file=f, defaults={"created_by": request.user}
    )
    for field in ("caption", "date_text", "place_text"):
        value = getattr(payload, field).strip()
        if value:
            setattr(item, field, value[:500])
    item.year = year_of(item.date_text) or item.year
    item.save()
    for t in payload.tags:
        person = _tree_person(project, t.person_id)
        last = GalleryTag.objects.filter(person=person).count()
        GalleryTag.objects.update_or_create(
            item=item, person=person, defaults={"relation": t.relation, "order": last}
        )
    return Status(201, _item_out(project, item))


class GalleryEdit(Schema):
    caption: str | None = None
    date_text: str | None = None
    place_text: str | None = None


@router.patch("/projects/{project_id}/gallery/{item_id}")
def edit_gallery_item(request: HttpRequest, project_id: UUID, item_id: UUID, payload: GalleryEdit):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    item = get_object_or_404(GalleryItem, pk=item_id, project=project)
    for field in ("caption", "date_text", "place_text"):
        value = getattr(payload, field)
        if value is not None:
            setattr(item, field, value.strip()[:500])
    item.year = year_of(item.date_text)
    item.save()
    return _item_out(project, item)


@router.post("/projects/{project_id}/gallery/{item_id}/tags", response={201: dict})
def tag_person(request: HttpRequest, project_id: UUID, item_id: UUID, payload: TagIn):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    item = get_object_or_404(GalleryItem, pk=item_id, project=project)
    person = _tree_person(project, payload.person_id)
    GalleryTag.objects.update_or_create(
        item=item, person=person,
        defaults={"relation": payload.relation,
                  "order": GalleryTag.objects.filter(person=person).count()},
    )  # fmt: skip
    return Status(201, _item_out(project, item))


@router.delete("/projects/{project_id}/gallery/{item_id}/tags/{person_id}", response={204: None})
def untag_person(request: HttpRequest, project_id: UUID, item_id: UUID, person_id: UUID):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    item = get_object_or_404(GalleryItem, pk=item_id, project=project)
    GalleryTag.objects.filter(item=item, person_id=person_id).delete()
    return Status(204, None)


@router.delete("/projects/{project_id}/gallery/{item_id}", response={204: None})
def remove_from_galleries(request: HttpRequest, project_id: UUID, item_id: UUID):
    """Take a picture out of every gallery. The file stays in the Archive."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    get_object_or_404(GalleryItem, pk=item_id, project=project).delete()
    return Status(204, None)


class OrderIn(Schema):
    item_ids: list[UUID]


@router.put("/projects/{project_id}/people/{person_id}/gallery/order")
def order_gallery(request: HttpRequest, project_id: UUID, person_id: UUID, payload: OrderIn):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    person = _tree_person(project, person_id)
    reorder(person, [str(i) for i in payload.item_ids])
    return person_gallery(project, person)


@router.get("/projects/{project_id}/photo-suggestions")
def photo_suggestions(
    request: HttpRequest, project_id: UUID, folder_id: UUID | None = None
) -> list[dict[str, Any]]:
    """Pictures in the Archive not yet in a gallery, with who each might show and why."""
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    return suggest_people(project, unplaced_images(project, folder_id))


# --- Explain this record, Life and times, offered explanations ---------------------


class ExplainIn(Schema):
    text: str
    year: int | None = None
    place: str = ""


@router.post("/explain")
def explain_view(request: HttpRequest, payload: ExplainIn) -> dict[str, Any]:
    """What a record says, what its words meant, what it may mean, and where to look."""
    text = payload.text.strip()
    if not text:
        raise HttpError(422, "Paste or choose the wording of the record.")
    if len(text) > 8000:
        raise HttpError(422, "That's too long to explain at once. Choose the part you need.")
    if payload.year is not None and not 1000 <= payload.year <= 2200:
        raise HttpError(422, "That year doesn't look right.")
    return explain_record(text, payload.year, payload.place[:200])


@router.get("/life-and-times")
def life_and_times_view(
    request: HttpRequest, year: int, project_id: UUID | None = None
) -> dict[str, Any]:
    """Prices, weather and what was happening in a year: context, not a fact about anyone."""
    if not 1000 <= year <= 2200:
        raise HttpError(422, "That year doesn't look right.")
    project = None
    if project_id:
        project = get_object_or_404(visible_projects(request.user), pk=project_id)
    return life_and_times(year, project)


class ExplanationIn(Schema):
    term: str
    meaning: str
    may_mean: str = ""
    where_to_look: str = ""
    area: str = ""
    period_from: int | None = None
    period_to: int | None = None
    sources: list[dict[str, str]] = []
    credit: str


@router.post("/explanations", response={201: dict})
def offer_explanation(request: HttpRequest, payload: ExplanationIn):
    """Offer an explanation for others. It's shown, with your credit, once reviewed."""
    if not payload.term.strip() or not payload.meaning.strip() or not payload.credit.strip():
        raise HttpError(422, "Give the term, what it meant and how you'd like to be credited.")
    if not payload.sources:
        raise HttpError(422, "Add at least one source, so others can check it.")
    sources = [
        {"title": str(s.get("title", ""))[:300], "url": str(s.get("url", ""))[:500]}
        for s in payload.sources[:10]
        if s.get("title")
    ]
    e = Explanation.objects.create(
        term=payload.term.strip()[:200],
        meaning=payload.meaning.strip()[:4000],
        may_mean=payload.may_mean.strip()[:2000],
        where_to_look=payload.where_to_look.strip()[:2000],
        area=payload.area.strip()[:200],
        period_from=payload.period_from,
        period_to=payload.period_to,
        sources=sources,
        author=request.user,
        credit=payload.credit.strip()[:200],
    )
    audit(request.user, "explanation.offer", e, term=e.term)
    note = "Thank you. It'll be shown, with your credit, once reviewed."
    return Status(201, {"id": str(e.id), "status": e.status, "note": note})


@router.get("/explanations/mine")
def my_explanations(request: HttpRequest) -> list[dict[str, Any]]:
    return [
        {"id": str(e.id), "term": e.term, "status": e.get_status_display(), "credit": e.credit}
        for e in Explanation.objects.filter(author=request.user)
    ]
