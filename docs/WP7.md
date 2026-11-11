# WP7 — Home and migration

From [SPEC.md](SPEC.md) (WP7), after Update 1's packages (ADR-048). Decisions in ADR-050.

## What was built (11 Nov 2026)

- **Homepages** at `/h/<address>/`: title, tagline, an about page and posts. Server-rendered by Django for speed and search engines, and readable on a phone. A homepage is off until its owner switches it on; while off, nothing on it can be seen.
- **Posts** are written in a small Markdown subset (headings, quotations, lists, bold, italic, http(s) links, attached pictures). Everything is HTML-escaped before the subset is turned into tags, so nothing typed or imported can add scripts. The editor has a preview. A draft's address follows its title until it's first published, then stays fixed so links keep working.
- **Approval flow.** Every post is a draft until its writer checks and approves it:
  - **Blockers** stop publishing: a picture whose rights aren't stated, a picture needing a credit with none, a picture in the text that isn't attached, no title, no words.
  - **Warnings** need the writer to tick that they've checked them: someone who may be living is named (anyone in their trees not recorded as dead), or a picture that's private in their Archive would become public.
  - The check at approval, and who approved it, are saved with the post. Editing a published post, or changing its pictures, takes it back to a draft. Posts can be taken down.
- **Pictures** come from the writer's Archive with a caption, a rights statement (mine; with permission; public domain or open licence; not sure) and a credit. They're served publicly only while attached to a published post on a live homepage, and only from the preview copy, which has had its camera data (including any GPS location) removed.
- **WordPress import** from the standard export file (WXR), parsed with `defusedxml`:
  - Posts (published, draft and private) come in as drafts; pages and attachments are skipped and counted.
  - HTML becomes the Markdown subset. Pictures aren't copied, because their rights need stating: each becomes a link to where it was.
  - The WordPress address is kept as the original (pages set `rel="canonical"` to it and show "First published at…") with its original date.
  - Old paths become redirects: `/h/<address>/2019/05/my-post/` sends a permanent redirect to the new post once it's published.
- **Prepared social posts** for a published post: a short one that fits 280 characters with the link, and a longer one with the summary. Copy and paste; ArchiveHub doesn't post for you yet.
- **Full export**: a zip of the homepage, each post as Markdown with its details as JSON (rights, credits, dates, original address), the original pictures and a redirects file.
- **Chat can draft**: a `draft_post` tool saves a draft when asked to write something up and returns its link. It can't publish.
- Account menu › Homepage opens the editor.

## Acceptance (SPEC.md)

| Done when | Status |
|---|---|
| Three historians have moved or published work and still have a full export route | Built and checked in the browser (set up, write, add a picture, check, publish, view on a phone, import a WordPress file, export). Needs three real historians: an owner action |

## Still to do

- **Collections** (groups of posts and Archive items with their own page).
- Direct posting to social platforms, one at a time, each with its terms read first.
- Copying WordPress pictures across with their rights stated, rather than linking to them.
- Custom domains, an RSS feed and a sitemap.
- Publishing a Life Report or Life Story as a post.
- Moderation and reporting for public pages (with WP8's forum tools).
