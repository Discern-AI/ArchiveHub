from datetime import datetime
from uuid import UUID

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from core.models import audit

from .models import Chat, Message, Project
from .permissions import editable_projects, visible_chats, visible_projects

router = Router()


# --- Schemas -----------------------------------------------------------------


class ProjectIn(Schema):
    title: str
    summary: str = ""


class ProjectPatch(Schema):
    title: str | None = None
    summary: str | None = None


class ProjectOut(Schema):
    id: UUID
    title: str
    summary: str
    visibility: str
    is_owner: bool
    created_at: datetime
    updated_at: datetime


class ChatIn(Schema):
    project_id: UUID | None = None
    title: str = ""


class ChatOut(Schema):
    id: UUID
    project_id: UUID | None
    title: str
    created_at: datetime
    updated_at: datetime


class MessageOut(Schema):
    id: UUID
    role: str
    content: str
    status: str
    created_at: datetime


class Me(Schema):
    id: UUID
    email: str
    display_name: str


def _project_out(project: Project, user) -> dict:
    return {
        "id": project.id,
        "title": project.title,
        "summary": project.summary,
        "visibility": project.visibility,
        "is_owner": project.owner_id == user.id,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def _clean_title(value: str) -> str:
    value = value.strip()
    if not value:
        raise HttpError(422, "Title can't be empty.")
    return value[:200]


# --- Me ----------------------------------------------------------------------


@router.get("/me", response=Me)
def me(request: HttpRequest):
    return request.user


# --- Projects ----------------------------------------------------------------


@router.get("/projects", response=list[ProjectOut])
def list_projects(request: HttpRequest):
    return [_project_out(p, request.user) for p in visible_projects(request.user)]


@router.post("/projects", response={201: ProjectOut})
def create_project(request: HttpRequest, payload: ProjectIn):
    project = Project.objects.create(
        owner=request.user, title=_clean_title(payload.title), summary=payload.summary.strip()
    )
    audit(request.user, "project.create", project)
    return Status(201, _project_out(project, request.user))


@router.get("/projects/{project_id}", response=ProjectOut)
def get_project(request: HttpRequest, project_id: UUID):
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    return _project_out(project, request.user)


@router.patch("/projects/{project_id}", response=ProjectOut)
def update_project(request: HttpRequest, project_id: UUID, payload: ProjectPatch):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    if payload.title is not None:
        project.title = _clean_title(payload.title)
    if payload.summary is not None:
        project.summary = payload.summary.strip()
    project.save()
    audit(request.user, "project.update", project)
    return _project_out(project, request.user)


@router.delete("/projects/{project_id}", response={204: None})
def delete_project(request: HttpRequest, project_id: UUID):
    # Only the owner may delete. The UI asks for confirmation first.
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    audit(request.user, "project.delete", project, title=project.title)
    project.delete()
    return Status(204, None)


# --- Chats -------------------------------------------------------------------


@router.get("/chats", response=list[ChatOut])
def list_chats(request: HttpRequest, project_id: UUID | None = None):
    chats = visible_chats(request.user)
    if project_id:
        chats = chats.filter(project_id=project_id)
    return chats


@router.post("/chats", response={201: ChatOut})
def create_chat(request: HttpRequest, payload: ChatIn):
    project = None
    if payload.project_id:
        project = get_object_or_404(editable_projects(request.user), pk=payload.project_id)
    chat = Chat.objects.create(owner=request.user, project=project, title=payload.title[:200])
    return Status(201, chat)


@router.get("/chats/{chat_id}", response=ChatOut)
def get_chat(request: HttpRequest, chat_id: UUID):
    return get_object_or_404(visible_chats(request.user), pk=chat_id)


@router.get("/chats/{chat_id}/messages", response=list[MessageOut])
def list_messages(request: HttpRequest, chat_id: UUID):
    chat = get_object_or_404(visible_chats(request.user), pk=chat_id)
    return Message.objects.filter(chat=chat)
