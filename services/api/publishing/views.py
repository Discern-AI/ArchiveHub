"""Public homepages and posts, rendered on the server for search engines and speed.

Only what's published on a homepage that's switched on is shown. Pictures are served
only when attached to a published post, and from the preview copy, which has had its
camera data (including any GPS location) removed.
"""

from __future__ import annotations

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from archive.models import Derivative

from .models import Homepage, PageStatus, Post, PostImage, Redirect
from .render import render as render_body


def _homepage(slug: str) -> Homepage:
    return get_object_or_404(Homepage, slug=slug, live=True)


def homepage(request: HttpRequest, slug: str) -> HttpResponse:
    h = _homepage(slug)
    posts = h.posts.filter(status=PageStatus.PUBLISHED)
    return render(request, "publishing/homepage.html", {
        "h": h,
        "about": render_body(h.about, lambda _id: None),
        "posts": posts,
    })  # fmt: skip


def post(request: HttpRequest, slug: str, post_slug: str) -> HttpResponse:
    h = _homepage(slug)
    p = Post.objects.filter(homepage=h, slug=post_slug, status=PageStatus.PUBLISHED).first()
    if p is None:
        r = Redirect.objects.filter(homepage=h, old_path__in=[f"/{post_slug}/", f"/{post_slug}"])
        if r.exists():
            return redirect(f"/h/{h.slug}/{r.first().post.slug}/", permanent=True)
        raise Http404
    images = {str(i.file_id): {"caption": i.caption, "credit": i.credit} for i in p.images.all()}
    body = render_body(
        p.body,
        lambda file_id: f"/h/{h.slug}/images/{file_id}" if file_id in images else None,
        images,
    )
    return render(request, "publishing/post.html", {"h": h, "p": p, "body": body})


def image(request: HttpRequest, slug: str, file_id: str) -> HttpResponse:
    h = _homepage(slug)
    used = PostImage.objects.filter(
        file_id=file_id, post__homepage=h, post__status=PageStatus.PUBLISHED
    ).exists()
    thumb = Derivative.objects.filter(file_id=file_id, kind="thumbnail").first() if used else None
    if thumb is None or not thumb.file_data:
        raise Http404
    response = HttpResponse(bytes(thumb.file_data), content_type="image/jpeg")
    response["Cache-Control"] = "public, max-age=3600"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def old_address(request: HttpRequest, slug: str, path: str) -> HttpResponse:
    """A link from the old blog, e.g. /h/jane/2019/05/my-post/: send it to the new post."""
    h = _homepage(slug)
    for candidate in (f"/{path}", f"/{path}/", f"/{path.rstrip('/')}"):
        r = Redirect.objects.filter(homepage=h, old_path=candidate).select_related("post").first()
        if r and r.post.status == PageStatus.PUBLISHED:
            return redirect(f"/h/{h.slug}/{r.post.slug}/", permanent=True)
    raise Http404
