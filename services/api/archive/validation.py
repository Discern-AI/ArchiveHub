"""Checks on upload: size, allowed types, and that a file's contents match its name.

Uploaded files are untrusted. We decide the kind from the bytes, not the filename,
and refuse anything we don't expect.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import PurePath

from django.conf import settings

ALLOWED = {
    ".pdf": "pdf",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
    ".gif": "image",
    ".tif": "image",
    ".tiff": "image",
    ".txt": "text",
    ".md": "text",
    ".csv": "text",
    ".docx": "docx",
    ".ged": "gedcom",
    ".mp3": "audio",
    ".m4a": "audio",
    ".wav": "audio",
    ".mp4": "video",
}

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "text": "text/plain; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "gedcom": "text/plain; charset=utf-8",
    "image": "application/octet-stream",
    "audio": "application/octet-stream",
    "video": "application/octet-stream",
}

IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"II*\x00": "image/tiff",
    b"MM\x00*": "image/tiff",
}


class Rejected(Exception):
    pass


@dataclass
class Checked:
    kind: str
    content_type: str


def _looks_like_text(head: bytes) -> bool:
    if head.startswith((b"\xff\xfe", b"\xfe\xff", b"\xef\xbb\xbf")):
        return True
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
        return True
    except UnicodeDecodeError:
        try:
            head.decode("cp1252")
            return True
        except UnicodeDecodeError:
            return False


def check_upload(name: str, size: int, path_or_file) -> Checked:
    """Return the checked kind and content type, or raise Rejected with a plain reason."""
    limit = settings.ARCHIVE_MAX_UPLOAD_MB * 1024 * 1024
    if size == 0:
        raise Rejected("The file is empty.")
    if size > limit:
        raise Rejected(f"Files can be up to {settings.ARCHIVE_MAX_UPLOAD_MB} MB.")
    ext = PurePath(name).suffix.lower()
    kind = ALLOWED.get(ext)
    if kind is None:
        allowed = ", ".join(sorted({e.lstrip(".") for e in ALLOWED}))
        raise Rejected(f"That type of file isn't supported yet. Allowed: {allowed}.")

    path_or_file.seek(0)
    head = path_or_file.read(4096)
    path_or_file.seek(0)

    if kind == "pdf":
        if not head.startswith(b"%PDF-"):
            raise Rejected("This doesn't look like a PDF.")
        return Checked("pdf", "application/pdf")
    if kind == "image":
        for sig, ctype in IMAGE_SIGNATURES.items():
            if head.startswith(sig):
                return Checked("image", ctype)
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            return Checked("image", "image/webp")
        raise Rejected("This doesn't look like an image file.")
    if kind == "docx":
        if not head.startswith(b"PK\x03\x04"):
            raise Rejected("This doesn't look like a Word document.")
        try:
            with zipfile.ZipFile(path_or_file) as zf:
                names = zf.namelist()
                total = sum(i.file_size for i in zf.infolist())
        except zipfile.BadZipFile as exc:
            raise Rejected("This Word document is damaged.") from exc
        finally:
            path_or_file.seek(0)
        if "word/document.xml" not in names:
            raise Rejected("This doesn't look like a Word document.")
        if total > 20 * limit:  # zip bomb guard
            raise Rejected("This document expands to an unsafe size.")
        return Checked("docx", CONTENT_TYPES["docx"])
    if kind in ("text", "gedcom"):
        if not _looks_like_text(head):
            raise Rejected("This doesn't look like a text file.")
        if kind == "gedcom" and b"0 HEAD" not in head.lstrip(b"\xef\xbb\xbf")[:64]:
            raise Rejected("This doesn't look like a GEDCOM family tree file.")
        return Checked(kind, CONTENT_TYPES[kind])
    if kind == "audio":
        if (
            head[:3] == b"ID3"
            or head[:2] == b"\xff\xfb"
            or head[4:8] == b"ftyp"
            or head[:4] == b"RIFF"
        ):
            return Checked("audio", "application/octet-stream")
        raise Rejected("This doesn't look like an audio file.")
    if kind == "video":
        if head[4:8] == b"ftyp":
            return Checked("video", "application/octet-stream")
        raise Rejected("This doesn't look like a video file.")
    raise Rejected("That type of file isn't supported yet.")
