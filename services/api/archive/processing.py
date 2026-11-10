"""What happens to a file after upload.

Cheap reading (text, PDF text layer, Word, GEDCOM detection, thumbnails) runs
automatically. OCR and AI handwriting reading only run after the user confirms an
estimate (SPEC §4, "show an estimate and ask before starting").
"""

from __future__ import annotations

import io
import logging
import shutil
import subprocess  # noqa: S404 - runs the local Tesseract binary with fixed arguments
import tempfile
from pathlib import Path

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from .models import (
    Derivative,
    FileAsset,
    FileKind,
    FileStatus,
    JobKind,
    JobStatus,
    ProcessingJob,
)

logger = logging.getLogger(__name__)

MIN_TEXT_PER_PAGE = 20  # less than this per page means scanned pages without a text layer
EXPENSIVE = {JobKind.OCR, JobKind.HANDWRITING}
MAX_AI_PAGES = 20


class JobFailed(Exception):
    """A failure with a message the user can act on."""


# --- Reading helpers -----------------------------------------------------------------


def _read_bytes(f: FileAsset) -> bytes:
    with f.original.open("rb") as fh:
        return fh.read()


def decode_text(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def pdf_text(data: bytes) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(f"[Page {i}]\n{t}" for i, t in enumerate(pages, 1) if t)
    return text, len(pages)


def docx_text(data: bytes) -> str:
    import zipfile

    from defusedxml import ElementTree

    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        root = ElementTree.fromstring(zf.read("word/document.xml"))
    paragraphs = []
    for p in root.iter(f"{ns}p"):
        text = "".join(t.text or "" for t in p.iter(f"{ns}t"))
        if text.strip():
            paragraphs.append(text)
    return "\n".join(paragraphs)


def make_thumbnail(data: bytes) -> tuple[bytes, dict]:
    """A small JPEG preview with all EXIF removed. The original is untouched."""
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = 120_000_000
    with Image.open(io.BytesIO(data)) as img:
        exif = img.getexif()
        meta = {
            "width": img.width,
            "height": img.height,
            "has_location_data": bool(exif.get_ifd(0x8825)) if exif else False,
        }
        taken = exif.get(0x0132) if exif else None  # DateTime
        if taken:
            meta["camera_date"] = str(taken)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((640, 640))
        out = io.BytesIO()
        img.convert("RGB").save(out, "JPEG", quality=82)  # saved without EXIF
    return out.getvalue(), meta


# --- After upload --------------------------------------------------------------------


def after_upload(f: FileAsset, user) -> ProcessingJob | None:
    """Mark the file checked and start cheap reading. Returns the job if one was started."""
    from .jobs import enqueue

    f.scan_note = scan_note()
    f.status = FileStatus.CHECKED
    f.save()
    if f.kind in (FileKind.TEXT, FileKind.PDF, FileKind.DOCX, FileKind.GEDCOM, FileKind.IMAGE):
        job = ProcessingJob.objects.create(
            file=f, kind=JobKind.EXTRACT, status=JobStatus.QUEUED, requested_by=user
        )
        enqueue(job.id)
        return job
    f.status_detail = "Stored safely. Transcribing audio and video comes in a later version."
    f.save()
    return None


def scan_note() -> str:
    # A malware scanner (e.g. ClamAV) plugs in here. Until one is configured we say so;
    # files stay private and are only ever served back as downloads.
    return "File type checked. No malware scanner is configured on this server yet."


# --- Estimates and confirmation ------------------------------------------------------


def estimate(f: FileAsset, kind: str) -> int:
    pages = f.page_count or 1
    if kind == JobKind.HANDWRITING:
        if pages > MAX_AI_PAGES:
            raise JobFailed(f"Handwriting reading handles up to {MAX_AI_PAGES} pages at a time.")
        return pages * settings.HANDWRITING_CREDITS_PER_PAGE
    if kind == JobKind.OCR:
        return pages * settings.OCR_CREDITS_PER_PAGE
    return 0


def allowed_jobs(f: FileAsset) -> list[str]:
    if f.kind == FileKind.IMAGE:
        return [JobKind.OCR, JobKind.HANDWRITING]
    if f.kind == FileKind.PDF:
        return [JobKind.HANDWRITING, JobKind.OCR]
    if f.kind == FileKind.GEDCOM:
        return [JobKind.GEDCOM_IMPORT]
    return []


# --- Running jobs --------------------------------------------------------------------


def run_job_in_worker(job_id) -> None:
    """Entry point for worker threads and RQ: they own their database connection."""
    close_old_connections()
    try:
        run_job(job_id)
    finally:
        close_old_connections()


def run_job(job_id) -> None:
    job = ProcessingJob.objects.select_related("file").filter(id=job_id).first()
    if job is None or job.status != JobStatus.QUEUED:
        return
    job.status = JobStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])
    f = job.file
    try:
        if job.kind == JobKind.EXTRACT:
            job.result = _extract(f)
        elif job.kind == JobKind.OCR:
            job.result = _ocr(f)
        elif job.kind == JobKind.HANDWRITING:
            job.result = _handwriting(f)
            job.credits_used = job.estimate_credits
        elif job.kind == JobKind.GEDCOM_IMPORT:
            from genealogy.importer import import_gedcom

            options = (job.result or {}).get("options", {})
            job.result = import_gedcom(
                f, job.requested_by, mode=options.get("mode", "new"), base=options.get("base", "")
            )
        job.status = JobStatus.DONE
    except JobFailed as exc:
        job.status, job.error = JobStatus.FAILED, str(exc)[:500]
    except Exception:
        logger.exception("Job %s failed", job.id)
        job.status, job.error = JobStatus.FAILED, "Something went wrong reading this file."
    job.save()
    if job.status == JobStatus.FAILED and f.status == FileStatus.CHECKED:
        f.status, f.status_detail = FileStatus.FAILED, job.error
        f.save()


def _extract(f: FileAsset) -> dict:
    data = _read_bytes(f)
    if f.kind == FileKind.IMAGE:
        try:
            thumb, meta = make_thumbnail(data)
        except Exception as exc:
            raise JobFailed("This image couldn't be opened.") from exc
        Derivative.objects.create(file=f, kind="thumbnail", method="thumbnail",
                                  engine="Pillow", file_data=thumb)  # fmt: skip
        f.metadata.update(meta)
        f.page_count = 1
        f.status = FileStatus.NEEDS_PROCESSING
        f.status_detail = "Preview made. Reading the text in an image is optional and uses credits."
        f.save()
        return {"thumbnail": True, **meta}

    page_count = None
    if f.kind == FileKind.PDF:
        try:
            text, page_count = pdf_text(data)
        except Exception as exc:
            raise JobFailed("This PDF couldn't be opened. It may be damaged or encrypted.") from exc
        method = "pdf_text"
    elif f.kind == FileKind.DOCX:
        try:
            text = docx_text(data)
        except Exception as exc:
            raise JobFailed("This Word document couldn't be read.") from exc
        method = "docx_text"
    else:
        text = decode_text(data)
        method = "gedcom_text" if f.kind == FileKind.GEDCOM else "plain_text"

    f.page_count = page_count
    scanned = f.kind == FileKind.PDF and len(text) < MIN_TEXT_PER_PAGE * max(page_count or 1, 1)
    if text.strip():
        Derivative.objects.create(file=f, kind="text", method=method, engine=method,
                                  text=text, page_count=page_count)  # fmt: skip
    if scanned:
        f.status = FileStatus.NEEDS_PROCESSING
        f.status_detail = (
            "These look like scanned pages with no text layer. "
            "Reading them is optional and uses credits."
        )
    elif f.kind == FileKind.GEDCOM:
        f.status = FileStatus.NEEDS_PROCESSING
        f.status_detail = "A family tree file. Import it to see the people and relationships."
    else:
        f.status, f.status_detail = FileStatus.INDEXED, ""
    f.save()
    return {"characters": len(text), "pages": page_count, "scanned": scanned}


def _ocr(f: FileAsset) -> dict:
    engine = shutil.which("tesseract")
    if engine is None:
        raise JobFailed(
            "Printed-text reading (OCR) isn't installed on this server yet. Nothing was charged."
        )
    if f.kind != FileKind.IMAGE:
        raise JobFailed(
            "Reading scanned PDFs needs OCRmyPDF, which isn't installed yet. Nothing was charged."
        )
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "page"
        src.write_bytes(_read_bytes(f))
        done = subprocess.run(  # noqa: S603 - fixed binary and arguments, no shell
            [engine, str(src), "stdout", "-l", "eng"],
            capture_output=True, timeout=300, check=False,
        )  # fmt: skip
    if done.returncode != 0:
        raise JobFailed("OCR couldn't read this image.")
    text = done.stdout.decode("utf-8", errors="replace").strip()
    Derivative.objects.create(file=f, kind="text", method="ocr", engine="tesseract", text=text,
                              note="Machine-read. Check it against the original.")  # fmt: skip
    f.status, f.status_detail = FileStatus.INDEXED, ""
    f.save()
    return {"characters": len(text)}


def _handwriting(f: FileAsset) -> dict:
    from .htr import transcribe

    text, model = transcribe(f, _read_bytes(f))
    Derivative.objects.create(
        file=f, kind="text", method="ai_handwriting", engine=model, text=text,
        note="AI transcription. Uncertain words are marked [?]. Check it against the original.",
    )  # fmt: skip
    f.status, f.status_detail = FileStatus.INDEXED, ""
    f.save()
    return {"characters": len(text), "model": model}


def confirm(job: ProcessingJob, user) -> None:
    from .jobs import enqueue

    job.status = JobStatus.QUEUED
    job.confirmed_by = user
    job.confirmed_at = timezone.now()
    job.save()
    enqueue(job.id)
