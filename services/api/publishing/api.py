"""Your homepage and posts: write, check, approve and publish; import from WordPress;
prepare social posts; export everything."""

from __future__ import annotations

import io
import json
import re
import zipfile
from typing import Any, Literal
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from ninja import File, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile

from archive.models import Derivative, FileAsset, FileKind
from core.models import audit
from projects.permissions import visible_projects

from .check import check_post
from .models import Homepage, PageStatus, Post, PostImage, Redirect
from .render import plain_text
from .wordpress import _unique_slug, import_wxr

router = Router()
RESERVED = {"admin", "api", "static", "h", "www", "archivehub"}


def _home(request: HttpRequest) -> Homepage:
    h = Homepage.objects.filter(owner=request.user).first()
    if h is None:
        raise HttpError(404, "Set up your homepage first.")
    return h


def _home_json(h: Homepage) -> dict[str, Any]:
    return {"slug": h.slug, "title": h.title, "tagline": h.tagline, "about": h.about,
            "live": h.live, "url": f"/h/{h.slug}/"}  # fmt: skip


def _post_json(p: Post, full: bool = False) -> dict[str, Any]:
    out = {
        "id": str(p.id), "title": p.title, "slug": p.slug, "summary": p.summary,
        "status": p.status, "source": p.source, "published_at": p.published_at,
        "original_url": p.original_url, "first_published": p.first_published,
        "url": f"/h/{p.homepage.slug}/{p.slug}/", "updated_at": p.updated_at,
    }  # fmt: skip
    if full:
        out["body"] = p.body
        out["images"] = [
            {"id": str(i.id), "file_id": str(i.file_id), "file_name": i.file.name,
             "caption": i.caption, "rights": i.rights, "credit": i.credit,
             "visibility": i.file.visibility}
            for i in p.images.select_related("file")
        ]  # fmt: skip
        out["approved_check"] = p.approved_check
    return out


@router.get("/home")
def get_home(request: HttpRequest) -> dict[str, Any] | None:
    h = Homepage.objects.filter(owner=request.user).first()
    return _home_json(h) if h else None


class HomeIn(Schema):
    slug: str
    title: str
    tagline: str = ""
    about: str = ""
    live: bool = False


@router.put("/home")
def save_home(request: HttpRequest, payload: HomeIn) -> dict[str, Any]:
    slug = slugify(payload.slug)[:60]
    if len(slug) < 3 or slug in RESERVED:
        raise HttpError(422, "Choose a web address of at least 3 letters or numbers.")
    if Homepage.objects.filter(slug=slug).exclude(owner=request.user).exists():
        raise HttpError(409, "That web address is taken. Try another.")
    if not payload.title.strip():
        raise HttpError(422, "Give your homepage a title.")
    h, _ = Homepage.objects.update_or_create(
        owner=request.user,
        defaults={"slug": slug, "title": payload.title.strip()[:200],
                  "tagline": payload.tagline.strip()[:300], "about": payload.about[:20000],
                  "live": payload.live},
    )  # fmt: skip
    return _home_json(h)


@router.get("/home/posts")
def list_posts(request: HttpRequest) -> list[dict[str, Any]]:
    return [_post_json(p) for p in _home(request).posts.all()]


class PostIn(Schema):
    title: str = ""
    summary: str = ""
    body: str = ""
    original_url: str = ""


@router.post("/home/posts", response={201: dict})
def create_post(request: HttpRequest, payload: PostIn):
    """A new draft. Nothing is public until it's checked and approved."""
    h = _home(request)
    p = Post.objects.create(homepage=h, title=payload.title.strip()[:300] or "Untitled",
                            slug=_unique_slug(h, payload.title or "post"),
                            summary=payload.summary[:500], body=payload.body[:100000])  # fmt: skip
    return Status(201, _post_json(p, full=True))


def _post(request: HttpRequest, post_id: UUID) -> Post:
    return get_object_or_404(Post, pk=post_id, homepage__owner=request.user)


@router.get("/home/posts/{post_id}")
def get_post(request: HttpRequest, post_id: UUID) -> dict[str, Any]:
    return _post_json(_post(request, post_id), full=True)


@router.patch("/home/posts/{post_id}")
def edit_post(request: HttpRequest, post_id: UUID, payload: PostIn) -> dict[str, Any]:
    """Edits to a published post take it back to draft, so the change is checked too."""
    p = _post(request, post_id)
    title = payload.title.strip()[:300] or p.title
    if title != p.title and p.published_at is None:
        # The address follows the title until it's first published, then stays put.
        p.slug = _unique_slug(p.homepage, title, exclude=p.pk)
    p.title = title
    p.summary = payload.summary[:500]
    p.body = payload.body[:100000]
    if payload.original_url and not payload.original_url.startswith(("http://", "https://")):
        raise HttpError(422, "The original's address should start with https://")
    p.original_url = payload.original_url
    if p.status == PageStatus.PUBLISHED:
        p.status = PageStatus.DRAFT
    p.save()
    return _post_json(p, full=True)


@router.delete("/home/posts/{post_id}", response={204: None})
def delete_post(request: HttpRequest, post_id: UUID):
    _post(request, post_id).delete()
    return Status(204, None)


class ImageIn(Schema):
    file_id: UUID
    caption: str = ""
    rights: Literal["own", "permission", "public_domain", "unclear"] = "unclear"
    credit: str = ""


@router.post("/home/posts/{post_id}/images", response={201: dict})
def attach_image(request: HttpRequest, post_id: UUID, payload: ImageIn):
    """Attach a picture from your Archive, saying whose it is."""
    p = _post(request, post_id)
    f = get_object_or_404(FileAsset, pk=payload.file_id, project__in=visible_projects(request.user))
    if f.kind != FileKind.IMAGE or not Derivative.objects.filter(file=f, kind="thumbnail").exists():
        raise HttpError(422, "Only pictures with a preview can go in a post.")
    i, _ = PostImage.objects.update_or_create(
        post=p, file=f, defaults={"caption": payload.caption[:500], "rights": payload.rights,
                                  "credit": payload.credit[:300]},
    )  # fmt: skip
    if p.status == PageStatus.PUBLISHED:
        p.status = PageStatus.DRAFT
        p.save(update_fields=["status", "updated_at"])
    return Status(201, {"id": str(i.id), "markdown": f"![{i.caption or f.name}](image:{f.id})"})


@router.delete("/home/posts/{post_id}/images/{image_id}", response={204: None})
def detach_image(request: HttpRequest, post_id: UUID, image_id: UUID):
    get_object_or_404(PostImage, pk=image_id, post=_post(request, post_id)).delete()
    return Status(204, None)


@router.post("/home/posts/{post_id}/check")
def check(request: HttpRequest, post_id: UUID) -> dict[str, Any]:
    """What must be fixed, and what needs your confirmation, before publishing."""
    return check_post(_post(request, post_id), request.user)


class PublishIn(Schema):
    confirm_warnings: bool = False


@router.post("/home/posts/{post_id}/publish")
def publish(request: HttpRequest, post_id: UUID, payload: PublishIn) -> dict[str, Any]:
    """Publish after the check: blockers must be fixed; warnings must be confirmed."""
    p = _post(request, post_id)
    result = check_post(p, request.user)
    if not result["ok"]:
        raise HttpError(422, " ".join(b["text"] for b in result["blockers"]))
    if result["warnings"] and not payload.confirm_warnings:
        raise HttpError(409, " ".join(w["text"] for w in result["warnings"]))
    p.status = PageStatus.PUBLISHED
    p.published_at = p.published_at or timezone.now()
    p.approved_by = request.user
    p.approved_check = {**result, "approved_at": timezone.now().isoformat()}
    p.save()
    audit(request.user, "post.publish", p, warnings=len(result["warnings"]))
    out = _post_json(p, full=True)
    if not p.homepage.live:
        out["note"] = "Published, but your homepage isn't switched on yet, so nobody can see it."
    return out


@router.post("/home/posts/{post_id}/unpublish")
def unpublish(request: HttpRequest, post_id: UUID) -> dict[str, Any]:
    p = _post(request, post_id)
    p.status = PageStatus.UNPUBLISHED
    p.save(update_fields=["status", "updated_at"])
    audit(request.user, "post.unpublish", p)
    return _post_json(p, full=True)


@router.get("/home/posts/{post_id}/social")
def social_posts(request: HttpRequest, post_id: UUID) -> dict[str, Any]:
    """Ready-to-paste posts for other sites. ArchiveHub doesn't post them for you yet."""
    p = _post(request, post_id)
    if p.status != PageStatus.PUBLISHED:
        raise HttpError(409, "Publish the post first, so the link works.")
    link = request.build_absolute_uri(f"/h/{p.homepage.slug}/{p.slug}/")
    words = p.summary or plain_text(p.body)
    short_room = 280 - len(link) - 2
    short = p.title if len(p.title) <= short_room else p.title[: short_room - 1] + "…"
    teaser = words if len(words) <= 300 else words[:297].rsplit(" ", 1)[0] + "…"
    return {
        "link": link,
        "posts": [
            {"for": "Short posts (X, Bluesky, Threads)", "text": f"{short}\n{link}", "limit": 280},
            {
                "for": "Longer posts (Facebook, LinkedIn, groups)",
                "text": f"{p.title}\n\n{teaser}\n\nRead more: {link}",
                "limit": None,
            },
        ],  # fmt: skip
        "note": "Copy and paste these yourself. Check pictures' rights before adding them there.",
    }


@router.post("/home/import/wordpress")
def import_wordpress(request: HttpRequest, file: File[UploadedFile]) -> dict[str, Any]:
    """Import a WordPress export (WXR) as drafts, with redirects from the old addresses."""
    h = _home(request)
    if file.size > 30 * 1024 * 1024:
        raise HttpError(422, "That file is too big (30 MB at most).")
    try:
        result = import_wxr(h, file.read())
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc
    audit(request.user, "home.import_wordpress", h, posts=result["count"])
    return result


@router.get("/home/export", response=None)
def export(request: HttpRequest) -> HttpResponse:
    """Everything on your homepage, to take anywhere: posts as Markdown with their details,
    their pictures, redirects and the homepage itself."""
    h = _home(request)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("homepage.json", json.dumps(_home_json(h), indent=2, ensure_ascii=False))
        for p in h.posts.all():
            meta = {k: (v.isoformat() if hasattr(v, "isoformat") else v)
                    for k, v in _post_json(p, full=True).items() if k != "body"}  # fmt: skip
            z.writestr(f"posts/{p.slug}.md", p.body)
            z.writestr(f"posts/{p.slug}.json", json.dumps(meta, indent=2, ensure_ascii=False))
            for i in p.images.select_related("file"):
                name = re.sub(r"[^\w.\- ]", "_", i.file.name)
                with i.file.original.open("rb") as src:
                    z.writestr(f"images/{i.file_id}-{name}", src.read())
        rows = ["old_path,new_path"] + [
            f"{r.old_path},/h/{h.slug}/{r.post.slug}/" for r in Redirect.objects.filter(homepage=h)
        ]
        z.writestr("redirects.csv", "\n".join(rows) + "\n")
        z.writestr("README.txt", "Your ArchiveHub homepage. Posts are Markdown (posts/*.md) "
                   "with their details beside them (posts/*.json); pictures are the originals "
                   "you uploaded; redirects.csv maps old addresses to new ones.\n")  # fmt: skip
    audit(request.user, "home.export", h)
    response = HttpResponse(buf.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{h.slug}-homepage.zip"'
    return response
