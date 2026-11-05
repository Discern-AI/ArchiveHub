# WP1 — Foundation: proposed plan

**Goal (gate):** a user can sign in, create a project and hold a saved, streamed chat.
**Out of scope:** history tables, connectors, uploads, Explorer, interviews, publishing, payments (WP2+).

## Folder structure

```
ArchiveHub/
├── apps/web/                      React + TS + Vite
│   ├── src/
│   │   ├── app/                   router, providers, layout shell
│   │   ├── components/            TopBar, Sidebar, Composer, RightPanel, MessageList, StarterPrompts
│   │   ├── features/auth/         sign in / sign up / sign out
│   │   ├── features/projects/     project list, project page
│   │   ├── features/chat/         chat view, SSE stream client
│   │   ├── lib/api.ts             typed client (generated from the OpenAPI schema)
│   │   └── styles/tokens.css      colours, type, spacing from the prototype
│   └── tests/
├── services/api/                  Django project
│   ├── archivehub/                settings (base/dev/test/prod), urls, asgi
│   ├── accounts/                  User (custom, email login), Profile
│   ├── projects/                  Project, ProjectMember, Chat, Message
│   ├── assistant/                 provider adapter, Anthropic provider, fake provider for tests, system prompt
│   ├── core/                      AuditLog, base models (UUID ids, timestamps)
│   └── tests/
├── infra/
│   ├── docker-compose.yml         db (Postgres 16 + PostGIS + pgvector), redis/valkey, api, web
│   └── db/Dockerfile              postgis image + pgvector
├── .github/workflows/ci.yml       ruff, pytest, eslint, prettier --check, vitest, tsc, build
├── .env.example
└── Makefile / scripts/            up, down, migrate, test, lint
```

## Data models (WP1 only)

All primary keys are UUIDs; every model has `created_at` / `updated_at`.

| Model | Fields | Notes |
|---|---|---|
| `accounts.User` | email (unique, login), display_name, is_active | Custom user from day one — painful to change later |
| `accounts.Profile` | user (1:1), bio, area, visibility (private default) | Public profile fields come in WP8 |
| `projects.Project` | owner, title, summary, visibility (private default) | |
| `projects.ProjectMember` | project, user, role (owner/editor/viewer) | Permission checks go through one helper used by every query |
| `projects.Chat` | project (nullable for loose chats), owner, title | |
| `projects.Message` | chat, role (user/assistant/tool), content, model, token counts, status (streaming/complete/error) | Saved as it streams so a dropped connection keeps partial output |
| `core.AuditLog` | actor, action, object type/id, data (no private text) | Records permission and project changes |

## API (Django Ninja, `/api/v1`)

Auth via allauth session cookies + CSRF (same-site SPA). `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}` (delete needs confirmation in UI), `GET/POST /chats`, `GET /chats/{id}/messages`, `POST /chats/{id}/messages` → `text/event-stream`.

## Frontend shell

Port the prototype's layout and palette into components: top bar (Search, Map, Forums, Archive, Account), left panel (New chat, Projects, Chats), centre chat with composer, collapsible right panel. The four starter prompts appear on an empty chat. Map, Forums, Archive, Search and Homepage routes exist as "coming in WP n" placeholders. Mobile: right panel becomes its own screen, left panel behind a menu. Reduced motion respected.

## Assistant in WP1

A provider interface (`stream(messages, system) -> events`) with an Anthropic implementation and a deterministic fake for tests. Model, max tokens and API key from environment. The system prompt carries the assistant rules from SPEC §6 (no invented records, say what wasn't checked). No tools yet — so it must say it can't search sources in this version.

## Dependencies (new in WP1)

Backend: Django 5 (BSD-3), django-ninja (MIT), django-allauth (MIT), psycopg 3 (LGPL-3.0, dynamic library), django-environ (MIT), anthropic (MIT), sentry-sdk (MIT), uvicorn (BSD-3), django-rq + rq (BSD-2; installed now, used from WP2), ruff (MIT), pytest + pytest-django (MIT/BSD-3), factory-boy (MIT).
Frontend: react, react-dom, react-router (MIT), @tanstack/react-query (MIT), tailwindcss (MIT), vite + @vitejs/plugin-react (MIT), typescript (Apache-2.0), eslint, prettier, vitest, @testing-library/react (MIT), openapi-typescript (MIT).
Infra: postgis/postgis:16 image (PostGIS GPL-2.0, separate service), pgvector (PostgreSQL licence), **Valkey** (BSD-3) instead of Redis to avoid Redis's 7.4+ licence change — Redis-protocol compatible, so RQ works unchanged.

All recorded in `DEPENDENCIES.md` as they're installed.

## Tests

- Auth: sign up, sign in, sign out; unauthenticated requests rejected.
- Permissions: a user can't read or write another user's project, chat or messages (every endpoint).
- Chat: streaming with the fake provider saves user and assistant messages; provider error leaves a saved error state.
- Frontend: shell renders; starter prompts hide after first message; composer sends; stream renders incrementally.
- CI runs all of the above on every push.

## Commit sequence

1. Repo docs (this commit set) · 2. Docker Compose + DB image · 3. Django skeleton, settings, CI · 4. Accounts + allauth · 5. Projects/chats models, permissions helper, API · 6. Assistant adapter + SSE endpoint · 7. React skeleton, tokens, shell · 8. Auth + projects UI · 9. Chat UI with streaming · 10. README setup guide, gate check.

## Needs from you before or during WP1

- An Anthropic API key for local `.env` (never committed).
- The prototype zip, for exact visual tokens.
- Whether Sentry and Railway accounts exist yet (can be wired later; not needed for the gate).
