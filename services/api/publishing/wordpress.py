"""Bring a WordPress blog across from its export file (WXR).

Posts come in as drafts, so each one goes through the pre-publish check and the
writer's approval before it's public. Their old addresses become redirects, and the
WordPress post is marked as the original until the writer says otherwise. Pictures
aren't copied (their rights need stating first): each becomes a link to where it was.
"""

from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

from defusedxml import ElementTree
from django.utils.text import slugify

from .models import Post, Redirect, Source

NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "wp": "http://wordpress.org/export/1.2/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
}


class _ToMarkdown(HTMLParser):
    """WordPress HTML to our Markdown subset. Unknown tags are dropped; their text kept."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.href: str | None = None
        self.link_text: list[str] = []
        self.images = 0

    def _put(self, s: str) -> None:
        (self.link_text if self.href is not None else self.out).append(s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("p", "div"):
            self.out.append("\n\n")
        elif tag == "br":
            self.out.append("\n")
        elif tag in ("h1", "h2"):
            self.out.append("\n\n## ")
        elif tag in ("h3", "h4", "h5", "h6"):
            self.out.append("\n\n### ")
        elif tag == "blockquote":
            self.out.append("\n\n> ")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in ("strong", "b"):
            self._put("**")
        elif tag in ("em", "i"):
            self._put("*")
        elif tag == "a" and (a.get("href") or "").startswith(("http://", "https://")):
            self.href = a["href"]
            self.link_text = []
        elif tag == "img" and (a.get("src") or "").startswith(("http://", "https://")):
            self.images += 1
            alt = (a.get("alt") or "picture").replace("[", "").replace("]", "")
            self.out.append(f"\n\n[Picture not copied across: {alt}]({a['src']})\n\n")

    def handle_endtag(self, tag):
        if tag in ("strong", "b"):
            self._put("**")
        elif tag in ("em", "i"):
            self._put("*")
        elif tag == "a" and self.href is not None:
            text = "".join(self.link_text).strip() or self.href
            self.out.append(f"[{text}]({self.href})")
            self.href = None
        elif tag in ("p", "div", "blockquote", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.out.append("\n\n")

    def handle_data(self, data):
        self._put(data.replace("\n", " ") if self.href is not None else data)


def html_to_markdown(text: str) -> tuple[str, int]:
    if "<" not in text:  # WordPress often stores plain paragraphs with blank lines
        return text.strip(), 0
    p = _ToMarkdown()
    p.feed(text)
    md = "".join(p.out)
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md, p.images


def _unique_slug(homepage, base: str, exclude=None) -> str:
    slug = (slugify(base) or "post")[:100]
    candidate, n = slug, 2
    taken = Post.objects.filter(homepage=homepage).exclude(pk=exclude)
    while taken.filter(slug=candidate).exists():
        candidate = f"{slug}-{n}"[:120]
        n += 1
    return candidate


def import_wxr(homepage, data: bytes) -> dict[str, Any]:
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ValueError("That doesn't look like a WordPress export file.") from exc
    channel = root.find("channel")
    if channel is None or channel.find("wp:wxr_version", NS) is None:
        raise ValueError("That doesn't look like a WordPress export file (WXR).")
    imported, skipped, images, redirects = [], 0, 0, 0
    for item in channel.findall("item"):
        kind = item.findtext("wp:post_type", default="", namespaces=NS)
        status = item.findtext("wp:status", default="", namespaces=NS)
        if kind != "post" or status not in ("publish", "draft", "private"):
            skipped += 1
            continue
        title = (item.findtext("title") or "").strip() or "Untitled"
        body, n_images = html_to_markdown(
            item.findtext("content:encoded", default="", namespaces=NS)
        )
        images += n_images
        excerpt = (item.findtext("excerpt:encoded", default="", namespaces=NS) or "").strip()
        link = (item.findtext("link") or "").strip()
        first = None
        if item.findtext("pubDate"):
            try:
                first = parsedate_to_datetime(item.findtext("pubDate"))
            except (TypeError, ValueError):
                first = None
        if first is None and item.findtext("wp:post_date_gmt", namespaces=NS):
            try:
                first = datetime.fromisoformat(item.findtext("wp:post_date_gmt", namespaces=NS))
            except ValueError:
                first = None
        slug = _unique_slug(homepage, item.findtext("wp:post_name", namespaces=NS) or title)
        post = Post.objects.create(
            homepage=homepage, title=title[:300], slug=slug, summary=excerpt[:500], body=body,
            source=Source.WORDPRESS,
            original_url=link if link.startswith(("http://", "https://")) else "",
            first_published=first if status == "publish" else None,
        )  # fmt: skip
        imported.append({"title": title, "slug": slug, "was_published": status == "publish"})
        path = urlparse(link).path if link else ""
        if path and path != "/":
            _, made = Redirect.objects.get_or_create(
                homepage=homepage, old_path=path[:500], defaults={"post": post}
            )
            redirects += 1 if made else 0
    return {
        "posts": imported,
        "count": len(imported),
        "skipped": skipped,
        "images_not_copied": images,
        "redirects": redirects,
        "note": "Posts came in as drafts: check and approve each before it's public. Pictures "
        "weren't copied; upload the ones you have the rights to and add them to the post.",
    }
