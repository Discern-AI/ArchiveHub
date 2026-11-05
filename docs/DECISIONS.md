# Architecture and product decisions

Each decision records what was chosen, what was considered and why. Read this and `SPEC.md` before changing the architecture. To change a decision, add a new entry that supersedes the old one rather than editing history.

"Spec" = *ArchiveHub Product and Build Specification*. "Blueprint" = *ArchiveHub Master Blueprint* v1.0. Both are in `docs/sources/`.

---

## ADR-001 — One shared platform, four user workflows
**Status:** Accepted · 2026-11-05
Record, Research, Home and Connect are activities on one account, one database and one assistant — not account types or separate codebases. Both inputs agree.

## ADR-002 — Frontend: React + TypeScript + Vite
**Status:** Accepted · 2026-11-05
**Considered:** Spec — Django templates + HTMX + Alpine, with small React islands. Blueprint — React + TS with Vite or Next.js.
**Decision:** React 18 + TypeScript + Vite, Tailwind CSS, TanStack Query. Public homepages are the exception (ADR-003).
**Why:** The prototype is already React/Vite. Mint is React + TS + Vite, so components may carry over. The interface (streaming chat, resizable panels, Explorer, live-interview animation) is too stateful for HTMX. The Spec justified Django/HTMX as "reusing the Mint stack", but Mint does not use Django (checked 2026-11-05). Next.js is unnecessary when Django serves public pages.

## ADR-003 — Backend: Django 5 (Python 3.12+) with Django Ninja
**Status:** Accepted · 2026-11-05
**Considered:** Spec — Django 5. Blueprint — FastAPI or NestJS. Also: reusing Mint's Express/Prisma API.
**Decision:** Django 5 with Django Ninja for the JSON API; Django templates only for public, SEO-relevant pages (homepages, posts) in WP7.
**Why:** The heavy lifting (Whisper, OCR, Docling, GEDCOM, Kraken) is Python. Django brings auth, migrations and an admin site that suits curating the source directory. Django Ninja gives typed, OpenAPI-documented endpoints close to the FastAPI style the Blueprint wanted.

## ADR-004 — Data: PostgreSQL 16 + PostGIS + pgvector
**Status:** Accepted · 2026-11-05
Spec named Postgres + pgvector; Blueprint added PostGIS. Both kept: one canonical store for relational truth, spatial queries (time map, coverage areas) and vector search. Postgres full-text first; OpenSearch only on measured need. Relational graph first; Apache AGE only if queries demand it.

## ADR-005 — Source records and assertions are kept separate
**Status:** Accepted · 2026-11-05
A record is evidence; a claim is an `Assertion` linked to evidence. Conflicting assertions coexist until a person decides, per project. An AI summary is never a source.

## ADR-006 — Federate before copying
**Status:** Accepted · 2026-11-05
Four access types (hosted, live API, metadata, external-only) with per-source storage policies. Nothing is stored beyond what a source's terms allow. No scraping against terms, no routing around paywalls.

## ADR-007 — First connectors and order
**Status:** Accepted · 2026-11-05
**Considered:** Spec — GB1900 hosted, then National Archives Discovery, then Wikidata. Blueprint — Europeana first, then TNA, then Wikidata.
**Decision:** GB1900 (hosted) → Wikidata → TNA Discovery (when access is approved; live search only, no caching, per its API terms) → Europeana (once key type and terms are confirmed).
**Why:** GB1900 is directly useful for Newbury and its Raw Dump is CC0, so it can be hosted outright. Europeana's coverage of a Berkshire street is thin, so it adds less to the pilot. All four remain in scope for WP3.

## ADR-008 — First slice and build order
**Status:** Accepted · 2026-11-05
**Considered:** Spec — WP1 foundation with streaming chat, WP2 the Pigeons research demo. Blueprint — prototype audit, foundation, Explorer over synthetic data, with the AI assistant at stage 5.
**Decision:** The Spec's WP1–WP8 order, absorbing the Blueprint's useful pieces: the prototype audit becomes part of WP1's interface shell; the connector contract test harness, data status labels and acceptance tests join WP2–WP3.
**Why:** The Pigeons demo proves what is distinctive (evidence, conflict, honesty about gaps). An Explorer over fake data doesn't.

## ADR-009 — Contributor payments: merged, phased model
**Status:** Accepted · 2026-11-05
**Considered:** Spec — fixed revenue pool; no automatic per-source donations at launch; if tested later, opt-in with a monthly cap. Blueprint — contracted royalty + opt-in 1p/5p/10p micro-donations with hard monthly caps + Community Heritage Fund.
**Decision:** Both, phased: (1) tips, support buttons and a "collections used" panel at launch, with usage logging from day one; (2) fixed revenue-share pool for 5–10 pilot partners, split by qualifying use; (3) opt-in capped per-source micro-support plus a Community Heritage Fund and open-source sponsorship. Full rules in SPEC §10.
**Why:** They don't really conflict — the Spec only objects to *automatic* per-source giving at *launch*, and the Blueprint's version is opt-in and capped. Phasing gives both. Where wording differed: "tip/support", not "donation", unless charity rules are met; micro-support is a separate billing line, never silently taken from credits.

## ADR-010 — Genealogy engine
**Status:** Accepted · 2026-11-05
**Considered:** Blueprint — evaluate Gramps Web API (AGPL-3.0) as the backend. Spec — Gramps family as reference only; permissive tree components.
**Decision:** Our own genealogy tables in `genealogy/` with GEDCOM 7 (and 5.5.1 where possible) import/export; Topola or family-chart for display; Gramps, webtrees and GeneWeb as design references only.
**Why:** AGPL obligations would reach into a commercial hosted service, and an API boundary doesn't automatically remove them. GEDCOM keeps users portable regardless.

## ADR-011 — Auth: Django auth + django-allauth
**Status:** Accepted · 2026-11-05
Blueprint wanted managed OIDC or hardened auth; Spec used Django accounts. django-allauth is mature, maintained and OIDC/social-capable, so we get both without writing security code.

## ADR-012 — Object storage: R2 in production, filesystem in dev
**Status:** Accepted · 2026-11-05
The Blueprint suggested MinIO for dev. MinIO's server is AGPL-3.0, so we avoid it. `django-storages` against Cloudflare R2 in production; Django's local file storage in development. Originals are immutable; derivatives stored separately.

## ADR-013 — Streaming
**Status:** Accepted · 2026-11-05
Chat streams over server-sent events (WP1). The live interview needs bidirectional audio, so WP5 adds WebSockets via Django Channels.

## ADR-014 — AI providers behind an adapter
**Status:** Accepted · 2026-11-05
Anthropic API for chat, reasoning and drafting; a lower-cost model (Mistral or similar) for bulk extraction and embeddings — all behind one provider interface so models are configuration, metered and testable.

## ADR-015 — No default public disclosure of living people; no facial recognition
**Status:** Accepted · 2026-11-05
Both inputs agree. Living people are hidden by default and flagged before publishing. No face matching across archives; identity links are user-confirmed and reversible.

## ADR-016 — Forums arrive with moderation, in WP8
**Status:** Accepted · 2026-11-05
Spec lists forums in Connect's first version; Blueprint defers them. They ship in WP8, only alongside reporting, moderation and block lists, and the moderation owner is named first (open decision).

## ADR-018 — Third-party facts are stored as our own claims with links, after checking
**Status:** Accepted · 2026-11-05 · decided by the owner
For sites whose reuse terms aren't confirmed (Pub Wiki, Closed Pubs, local blogs), ArchiveHub stores only short factual claims written in our own words, each linked to the page it came from. No copied text, page layouts or photos. Every claim is checked against the live page before it is stored, with the date checked recorded. Anything that can't be checked (e.g. a page that blocks access) is not stored. Pub Wiki's pages say "All rights reserved", so this stays reference-only until permission is agreed; invite the site owners as contributors (DATA_SOURCES.md).

## ADR-019 — Places use latitude/longitude until the time map
**Status:** Accepted · 2026-11-05
PostGIS geometry needs GeoDjango and GDAL, which add setup cost before anything uses spatial queries. Until WP6, `Place` stores latitude, longitude and a geocode precision; WP6 migrates these to PostGIS geometry (ADR-004 still stands).

## ADR-020 — Citations and "What I checked" are built by the server
**Status:** Accepted · 2026-11-05
The assistant cites records with numbers that the server assigns when a tool returns them. The sources list and the "What I checked" block are built from the actual tool calls and results, not from the model's text. A number the model writes that no tool returned is never shown as a source, so the model cannot invent a link.

## ADR-021 — GB1900: the CC0 raw dump, under our own name
**Status:** Accepted · 2026-11-05
**Considered:** the Complete/Abridged GB1900 Gazetteer (CC BY-SA) or the Raw Dump (CC0).
**Decision:** Host the Raw Dump. Our dataset is called "Old map names (OS six-inch, c.1900)" and cites "GB1900 final raw gazetteer data dump, made available by the GB1900 Project".
**Why:** CC BY-SA's share-alike could reach data we combine with it (SPEC §11). The raw dump is CC0; its only condition is that derived works must not use "GB1900" in their name. We keep each pin's most agreed reading plus variants and coordinates, never contributor IDs. Import is limited to Newbury and West Berkshire by default (15,188 labels); `--all` loads Great Britain.

## ADR-022 — Live connectors verify TLS with the OS trust store
**Status:** Accepted · 2026-11-05
Python's OpenSSL built an expired certificate chain from the Windows store for wikidata.org, while Windows' own verifier accepted it. Connectors use `truststore` (MIT), which verifies with the operating system's chain building. Verification is never disabled; a test asserts it.

## ADR-023 — Explorer pages by server cursor; virtualised table later
**Status:** Accepted · 2026-11-05
The Explorer pages 25 records at a time with server-side keyset cursors (stable across millions of rows). A virtualised infinite-scroll table (TanStack Virtual) is deferred until a dataset needs continuous scrolling; the cursor API already supports it.

## ADR-024 — Jobs: thread locally, inline in tests, RQ in production
**Status:** Accepted · 2026-11-05
Processing runs through one `enqueue` function with three backends: `thread` (local development without Redis), `sync` (tests, deterministic) and `rq` (production on Redis/Valkey). Jobs that use credits are created as "waiting for your go-ahead" with an estimate and only run after explicit confirmation.

## ADR-025 — Our own GEDCOM reader; unknown counts as living
**Status:** Accepted · 2026-11-05
A small parser in `genealogy/gedcom.py` (GEDCOM 5.5.1/7 line format) avoids GPL libraries (ADR-010). Every imported fact becomes a claim whose evidence is the file and the GEDCOM record; corrections are new claims beside it. A person with no recorded death or burial who may have been born within the last 110 years (or has no birth date) is treated as living, so private, and never shown to the assistant.

## ADR-026 — Say plainly what isn't installed
**Status:** Accepted · 2026-11-05
No malware scanner, OCR engine or PDF rasteriser is installed yet. Uploads record "No malware scanner is configured on this server yet"; OCR fails with "isn't installed" and charges nothing. Files stay private and are only served back as downloads (`nosniff`, sandboxed CSP), never rendered inline. A scanner (e.g. ClamAV) must be in place before any public launch.

## ADR-027 — Credits are estimated and recorded, not yet charged
**Status:** Accepted · 2026-11-05
Jobs record their estimate and the credits used. The credit balance and ledger come in WP8; until then nothing is deducted. The confirmation step is already in place so the behaviour won't change for users when charging starts.

## ADR-017 — Prototype kept as reference only
**Status:** Accepted · 2026-11-05
The prototype lives untouched in `prototype-reference/`. It's the visual reference; its scripted replies and sample data are not architecture. The real app is built in `apps/web` and replaces simulated flows one at a time.
