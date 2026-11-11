"""The check before anything is published.

Blockers stop publishing until fixed: a picture whose rights aren't stated, a picture
that needs a credit and has none, or a picture in the post that isn't attached to it.
Warnings need the writer's explicit confirmation: a person who may be living is named,
or a file that's private in the Archive would become public.
"""

from __future__ import annotations

import re
from typing import Any

from history.models import LivingStatus, Person
from projects.permissions import visible_projects

from .models import ImageRights, Post
from .render import IMAGE, plain_text


def _named(text: str, name: str) -> bool:
    words = name.split()
    if len(words) < 2:
        return False  # a single name matches too much to be useful
    return bool(re.search(rf"(?<![\w]){re.escape(name)}(?![\w])", text, re.IGNORECASE))


def check_post(post: Post, user) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    text = f"{post.title}\n{plain_text(post.body)}\n{post.summary}"
    seen = set()
    living = (
        Person.objects.filter(project__in=visible_projects(user))
        .exclude(living_status=LivingStatus.DECEASED)
        .select_related("project")
    )
    for p in living:
        if p.name in seen or not _named(text, p.name):
            continue
        seen.add(p.name)
        warnings.append({
            "kind": "living",
            "text": f"{p.name} may be living (from your tree “{p.project.title}”). Only publish "
            "with their agreement, and leave out private details.",
        })  # fmt: skip
    attached = {str(i.file_id): i for i in post.images.select_related("file")}
    for line in post.body.splitlines():
        m = IMAGE.match(line.strip())
        if m and m.group("id") not in attached:
            blockers.append({"kind": "image", "text": "A picture in the post isn't attached to it, "
                             "so its rights aren't known. Attach it or remove it."})  # fmt: skip
    for i in attached.values():
        name = i.file.name
        if i.rights == ImageRights.UNCLEAR:
            blockers.append({"kind": "rights", "text": f"Say whose picture “{name}” is and whether "
                             "you can publish it."})  # fmt: skip
        elif (
            i.rights in (ImageRights.PERMISSION, ImageRights.PUBLIC_DOMAIN) and not i.credit.strip()
        ):
            blockers.append({"kind": "credit", "text": f"Add a credit for “{name}” (who made it, "
                             "and where it's from)."})  # fmt: skip
        if i.file.visibility == "private":
            warnings.append({"kind": "private", "text": f"“{name}” is private in your Archive. "
                             "Publishing shows this picture to everyone."})  # fmt: skip
    if not post.title.strip():
        blockers.append({"kind": "title", "text": "Give the post a title."})
    if not plain_text(post.body):
        blockers.append({"kind": "empty", "text": "The post has no words yet."})
    return {"ok": not blockers, "blockers": blockers, "warnings": warnings}
