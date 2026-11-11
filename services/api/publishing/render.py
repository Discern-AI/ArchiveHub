"""Posts are written in a small Markdown subset and rendered here, safely.

Everything is HTML-escaped first, so nothing a writer (or an imported blog) types can
add scripts or styles. Then only these are turned into HTML:

    ## Heading            ### Smaller heading
    > A quotation          - A list item
    **bold**  *italic*     [link text](https://example.org)
    ![caption](image:FILE-ID)   on its own line: a picture attached to the post

Links must be http or https. Pictures must be attached to the post (with their rights
stated), and are served from the homepage's own address.
"""

from __future__ import annotations

import html
import re

IMAGE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\(image:(?P<id>[0-9a-f-]{36})\)$")
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
BOLD = re.compile(r"\*\*(.+?)\*\*")
ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _inline(text: str) -> str:
    out = html.escape(text, quote=True)
    # Links: the escaped URL is safe in an attribute; only http(s) were matched.
    out = LINK.sub(
        lambda m: f'<a href="{m.group(2)}" rel="nofollow noopener">{m.group(1)}</a>', out
    )
    out = BOLD.sub(r"<strong>\1</strong>", out)
    out = ITALIC.sub(r"<em>\1</em>", out)
    return out


def render(body: str, image_url, captions: dict[str, dict] | None = None) -> str:
    """HTML for a post body. `image_url(file_id)` gives a picture's public address, or
    None if it isn't attached (then the picture is left out)."""
    captions = captions or {}
    blocks = re.split(r"\n\s*\n", body.replace("\r\n", "\n").strip())
    out = []
    for block in blocks:
        lines = [line.rstrip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        first = lines[0]
        if len(lines) == 1 and IMAGE.match(first.strip()):
            m = IMAGE.match(first.strip())
            url = image_url(m.group("id"))
            if url:
                meta = captions.get(m.group("id"), {})
                caption = meta.get("caption") or m.group("alt")
                credit = meta.get("credit", "")
                cap = html.escape(caption) + (
                    f' <span class="credit">{html.escape(credit)}</span>' if credit else ""
                )
                out.append(
                    f'<figure><img src="{html.escape(url)}" alt="{html.escape(caption)}" '
                    f'loading="lazy"><figcaption>{cap}</figcaption></figure>'
                )
            continue
        if first.startswith("### "):
            out.append(f"<h3>{_inline(first[4:])}</h3>")
            lines = lines[1:]
        elif first.startswith("## "):
            out.append(f"<h2>{_inline(first[3:])}</h2>")
            lines = lines[1:]
        if not lines:
            continue
        if all(line.startswith("> ") or line == ">" for line in lines):
            quoted = "<br>".join(_inline(line[2:]) for line in lines)
            out.append(f"<blockquote><p>{quoted}</p></blockquote>")
        elif all(line.startswith("- ") for line in lines):
            items = "".join(f"<li>{_inline(line[2:])}</li>" for line in lines)
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{'<br>'.join(_inline(line) for line in lines)}</p>")
    return "\n".join(out)


def plain_text(body: str) -> str:
    """The words without formatting, for summaries and checks."""
    text = re.sub(r"!\[[^\]]*\]\(image:[^)]*\)", "", body)
    text = LINK.sub(r"\1", text)
    text = re.sub(r"[*#>]+", "", text)
    return " ".join(text.replace("- ", " ").split())
