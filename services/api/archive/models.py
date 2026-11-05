"""The Archive: a project's private files. Originals are never changed (SPEC §7);
everything derived from them is stored separately with how it was made."""

import uuid

from django.conf import settings
from django.db import models

from core.models import BaseModel, Visibility


def original_path(instance: "FileAsset", filename: str) -> str:
    # Random storage name: the user's filename is kept in `name`, never used as a path.
    return f"originals/{instance.project_id}/{uuid.uuid4().hex}"


class Folder(BaseModel):
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="folders"
    )
    name = models.CharField(max_length=200)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="unique_folder_name")
        ]

    def __str__(self) -> str:
        return self.name


class FileStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    CHECKED = "checked", "Checked"
    INDEXED = "indexed", "Read and indexed"
    NEEDS_PROCESSING = "needs_processing", "Ready to process"
    REJECTED = "rejected", "Rejected"
    FAILED = "failed", "Couldn't be read"


class FileKind(models.TextChoices):
    PDF = "pdf", "PDF"
    IMAGE = "image", "Image"
    TEXT = "text", "Text"
    DOCX = "docx", "Word document"
    GEDCOM = "gedcom", "Family tree (GEDCOM)"
    AUDIO = "audio", "Audio"
    VIDEO = "video", "Video"
    OTHER = "other", "Other"


class FileAsset(BaseModel):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="files")
    folder = models.ForeignKey(
        Folder, null=True, blank=True, on_delete=models.SET_NULL, related_name="files"
    )
    name = models.CharField(max_length=255)
    original = models.FileField(upload_to=original_path)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    kind = models.CharField(max_length=10, choices=FileKind.choices)
    content_type = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=FileStatus.choices, default=FileStatus.UPLOADED
    )
    status_detail = models.CharField(max_length=300, blank=True)
    scan_note = models.CharField(max_length=300, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class Derivative(BaseModel):
    """Something made from an original: extracted text, OCR, an AI transcription.
    Several can exist side by side; none replaces the original."""

    file = models.ForeignKey(FileAsset, on_delete=models.CASCADE, related_name="derivatives")
    kind = models.CharField(max_length=20)  # text | thumbnail
    method = models.CharField(
        max_length=30
    )  # pdf_text | docx_text | plain_text | ocr | ai_handwriting
    engine = models.CharField(max_length=100, blank=True)
    text = models.TextField(blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    file_data = models.BinaryField(null=True, blank=True)  # small derivatives (thumbnails)

    class Meta:
        ordering = ["-created_at"]


class JobKind(models.TextChoices):
    EXTRACT = "extract", "Read text"
    OCR = "ocr", "Read printed text (OCR)"
    HANDWRITING = "handwriting", "Read handwriting (AI)"
    GEDCOM_IMPORT = "gedcom_import", "Import family tree"


class JobStatus(models.TextChoices):
    AWAITING_CONFIRMATION = "awaiting_confirmation", "Waiting for your go-ahead"
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    DONE = "done", "Done"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class ProcessingJob(BaseModel):
    file = models.ForeignKey(FileAsset, on_delete=models.CASCADE, related_name="jobs")
    kind = models.CharField(max_length=20, choices=JobKind.choices)
    status = models.CharField(max_length=25, choices=JobStatus.choices)
    estimate_credits = models.PositiveIntegerField(default=0)
    credits_used = models.PositiveIntegerField(default=0)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
