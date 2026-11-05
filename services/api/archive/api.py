"""The Archive: folders, uploads, previews and processing jobs. Everything is private to
the project; nothing here is ever public."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile

from core.models import audit
from projects.permissions import editable_projects, visible_projects

from .models import Derivative, FileAsset, Folder, JobKind, JobStatus, ProcessingJob
from .processing import EXPENSIVE, JobFailed, after_upload, allowed_jobs, confirm, estimate
from .validation import Rejected, check_upload

router = Router()


def _files_for(user, editable: bool = False):
    projects = editable_projects(user) if editable else visible_projects(user)
    return FileAsset.objects.filter(project__in=projects)


def _jobs_for(user):
    return ProcessingJob.objects.filter(file__project__in=editable_projects(user))


# --- Schemas -----------------------------------------------------------------------


class FolderIn(Schema):
    name: str


class FolderOut(Schema):
    id: UUID
    name: str


class JobOut(Schema):
    id: UUID
    kind: str
    status: str
    estimate_credits: int
    credits_used: int
    error: str
    result: dict
    created_at: datetime


class FileOut(Schema):
    id: UUID
    name: str
    folder_id: UUID | None
    kind: str
    size: int
    status: str
    status_detail: str
    scan_note: str
    page_count: int | None
    has_preview: bool
    created_at: datetime


def _file_out(f: FileAsset) -> dict[str, Any]:
    return {
        "id": f.id,
        "name": f.name,
        "folder_id": f.folder_id,
        "kind": f.kind,
        "size": f.size,
        "status": f.status,
        "status_detail": f.status_detail,
        "scan_note": f.scan_note,
        "page_count": f.page_count,
        "has_preview": f.derivatives.filter(kind="thumbnail").exists(),
        "created_at": f.created_at,
    }


# --- Folders -----------------------------------------------------------------------


@router.get("/projects/{project_id}/folders", response=list[FolderOut])
def list_folders(request: HttpRequest, project_id: UUID):
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    return Folder.objects.filter(project=project)


@router.post("/projects/{project_id}/folders", response={201: FolderOut})
def create_folder(request: HttpRequest, project_id: UUID, payload: FolderIn):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    name = payload.name.strip()[:200]
    if not name:
        raise HttpError(422, "Give the folder a name.")
    folder, _ = Folder.objects.get_or_create(project=project, name=name)
    return Status(201, folder)


# --- Files -------------------------------------------------------------------------


@router.get("/projects/{project_id}/files", response=list[FileOut])
def list_files(request: HttpRequest, project_id: UUID, folder_id: UUID | None = None):
    project = get_object_or_404(visible_projects(request.user), pk=project_id)
    files = FileAsset.objects.filter(project=project)
    if folder_id:
        files = files.filter(folder_id=folder_id)
    return [_file_out(f) for f in files]


@router.post("/projects/{project_id}/files", response={201: FileOut})
def upload_file(
    request: HttpRequest,
    project_id: UUID,
    file: File[UploadedFile],
    folder_id: Form[UUID | None] = None,
):
    project = get_object_or_404(editable_projects(request.user), pk=project_id)
    folder = None
    if folder_id:
        folder = get_object_or_404(Folder, pk=folder_id, project=project)
    name = (file.name or "upload").replace("\\", "/").rsplit("/", 1)[-1][:255]
    try:
        checked = check_upload(name, file.size, file)
    except Rejected as exc:
        raise HttpError(422, str(exc)) from exc
    digest = hashlib.sha256()
    for chunk in file.chunks():
        digest.update(chunk)
    file.seek(0)
    asset = FileAsset(
        project=project, folder=folder, name=name, size=file.size, sha256=digest.hexdigest(),
        kind=checked.kind, content_type=checked.content_type, uploaded_by=request.user,
    )  # fmt: skip
    asset.original.save(name, file, save=False)
    asset.save()
    audit(request.user, "file.upload", asset, kind=asset.kind, size=asset.size)
    after_upload(asset, request.user)
    asset.refresh_from_db()
    return Status(201, _file_out(asset))


@router.get("/files/{file_id}")
def file_detail(request: HttpRequest, file_id: UUID) -> dict[str, Any]:
    f = get_object_or_404(_files_for(request.user), pk=file_id)
    texts = Derivative.objects.filter(file=f, kind="text")
    return {
        **_file_out(f),
        "sha256": f.sha256,
        "metadata": f.metadata,
        "texts": [
            {
                "id": str(d.id),
                "method": d.method,
                "engine": d.engine,
                "note": d.note,
                "text": d.text[:200_000],
                "created_at": d.created_at.isoformat(),
            }
            for d in texts
        ],  # fmt: skip
        "jobs": [JobOut.from_orm(j).dict() for j in f.jobs.all()],
        "can_process": [{"kind": k, "label": JobKind(k).label} for k in allowed_jobs(f)],
    }


class FilePatch(Schema):
    name: str | None = None
    folder_id: UUID | None = None
    clear_folder: bool = False


@router.patch("/files/{file_id}", response=FileOut)
def update_file(request: HttpRequest, file_id: UUID, payload: FilePatch):
    f = get_object_or_404(_files_for(request.user, editable=True), pk=file_id)
    if payload.name is not None and payload.name.strip():
        f.name = payload.name.strip()[:255]
    if payload.clear_folder:
        f.folder = None
    elif payload.folder_id:
        f.folder = get_object_or_404(Folder, pk=payload.folder_id, project=f.project)
    f.save()
    return _file_out(f)


@router.delete("/files/{file_id}", response={204: None})
def delete_file(request: HttpRequest, file_id: UUID):
    """Deletes the file and what was made from it. The UI asks for confirmation first."""
    f = get_object_or_404(_files_for(request.user, editable=True), pk=file_id)
    audit(request.user, "file.delete", f, name=f.name, sha256=f.sha256)
    f.original.delete(save=False)
    f.delete()
    return Status(204, None)


@router.get("/files/{file_id}/original", response=None)
def download_original(request: HttpRequest, file_id: UUID) -> FileResponse:
    f = get_object_or_404(_files_for(request.user), pk=file_id)
    # Always a download, never rendered inline: uploads are untrusted.
    response = FileResponse(f.original.open("rb"), as_attachment=True, filename=f.name,
                            content_type="application/octet-stream")  # fmt: skip
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response


@router.get("/files/{file_id}/preview", response=None)
def preview(request: HttpRequest, file_id: UUID) -> HttpResponse:
    f = get_object_or_404(_files_for(request.user), pk=file_id)
    thumb = Derivative.objects.filter(file=f, kind="thumbnail").first()
    if thumb is None or not thumb.file_data:
        raise HttpError(404, "No preview.")
    response = HttpResponse(bytes(thumb.file_data), content_type="image/jpeg")
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, max-age=3600"
    return response


# --- Jobs --------------------------------------------------------------------------


class JobIn(Schema):
    kind: str


@router.post("/files/{file_id}/jobs", response={201: JobOut})
def request_job(request: HttpRequest, file_id: UUID, payload: JobIn):
    """Start processing. Anything that uses credits waits for confirmation."""
    f = get_object_or_404(_files_for(request.user, editable=True), pk=file_id)
    if payload.kind not in allowed_jobs(f):
        raise HttpError(422, "That can't be done to this file.")
    try:
        credits = estimate(f, payload.kind)
    except JobFailed as exc:
        raise HttpError(422, str(exc)) from exc
    needs_ok = payload.kind in EXPENSIVE
    job = ProcessingJob.objects.create(
        file=f, kind=payload.kind, requested_by=request.user, estimate_credits=credits,
        status=JobStatus.AWAITING_CONFIRMATION if needs_ok else JobStatus.QUEUED,
    )  # fmt: skip
    if not needs_ok:
        confirm(job, request.user)
        job.refresh_from_db()
    return Status(201, job)


@router.post("/jobs/{job_id}/confirm", response=JobOut)
def confirm_job(request: HttpRequest, job_id: UUID):
    job = get_object_or_404(_jobs_for(request.user), pk=job_id)
    if job.status != JobStatus.AWAITING_CONFIRMATION:
        raise HttpError(409, "This job isn't waiting for confirmation.")
    audit(request.user, "job.confirm", job, kind=job.kind, credits=job.estimate_credits)
    confirm(job, request.user)
    job.refresh_from_db()
    return job


@router.post("/jobs/{job_id}/cancel", response=JobOut)
def cancel_job(request: HttpRequest, job_id: UUID):
    job = get_object_or_404(_jobs_for(request.user), pk=job_id)
    if job.status not in (JobStatus.AWAITING_CONFIRMATION, JobStatus.QUEUED):
        raise HttpError(409, "This job can't be cancelled now.")
    job.status = JobStatus.CANCELLED
    job.save()
    return job
