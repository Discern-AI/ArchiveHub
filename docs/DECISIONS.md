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

## ADR-017 — Prototype kept as reference only
**Status:** Accepted · 2026-11-05
The prototype lives untouched in `prototype-reference/`. It's the visual reference; its scripted replies and sample data are not architecture. The real app is built in `apps/web` and replaces simulated flows one at a time.
