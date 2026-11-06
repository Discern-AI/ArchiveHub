# ArchiveHub

A chat-first platform where people preserve family and local history, research the past, publish their work and find the people who can help. Piloting in Newbury and West Berkshire.

**Status:** WP6 (Time map and Search). Open **Map** to move through Cheap Street by year, with public records and your private memories and photos kept visibly apart, and today's map alongside. **Search** looks across everything you're allowed to see and says what it searched. See [docs/WP6.md](docs/WP6.md), [WP5](docs/WP5.md), [WP4](docs/WP4.md), [WP3](docs/WP3.md) and [WP2](docs/WP2.md).

For historic OS maps on the time map, set `MAPTILER_KEY` (see [docs/WP6.md](docs/WP6.md)). Without it, the map shows today with names from the c.1900 map.

For interviews, install speech recognition: `pip install -r requirements-speech.txt` (about 600 MB of models download on first use). Or set `SPEECH_PROVIDER=fake` to try it offline.

Optional: install [Tesseract](https://github.com/tesseract-ocr/tesseract) for printed-text OCR. Without it, OCR jobs say so and charge nothing.

## Documentation

- [docs/SPEC.md](docs/SPEC.md) — product and build specification
- [docs/DECISIONS.md](docs/DECISIONS.md) — architecture and product decisions
- [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) — historical data sources and their status
- [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) — third-party code and licences
- [docs/WP1_PLAN.md](docs/WP1_PLAN.md) — the current work package
- [CLAUDE.md](CLAUDE.md) — rules for coding assistants
- [prototype-reference/](prototype-reference/) — the original interface prototype (visual reference only)

## Running it locally

You need **Python 3.12+** and **Node 20+**. Docker is optional (only for Postgres and the job queue).

### 1. API (Django) — `services/api`

```bash
cd services/api
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy ..\..\.env.example .env      # macOS/Linux: cp ../../.env.example .env
```

Edit `.env`: add your `ANTHROPIC_API_KEY`, or set `ASSISTANT_PROVIDER=fake` to work offline (the fake assistant echoes your message).

```bash
python manage.py migrate
python manage.py load_reference_data   # source directory + checked Cheap Street facts
# Optional: old OS map names (see docs/WP3.md for the download)
python manage.py import_old_map_names --zip var/downloads/gb1900/GB1900_final_raw_dump_july_2018.zip
python manage.py createsuperuser   # optional: for /admin
# Optional: compare speech engines on consented recordings (docs/WP5.md)
python manage.py speech_spike --dir var/speech-spike --engine whisper:base.en --engine whisper:small.en
uvicorn archivehub.asgi:application --reload --port 8000
```

Use uvicorn rather than `runserver`: chat replies stream over an async view, which Django's development server would buffer.

### 2. Web app (React) — `apps/web`

```bash
cd apps/web
npm install
npm run dev
```

Open <http://localhost:5173>, create an account and start a chat. Vite forwards `/api`, `/ws`, `/_allauth` and `/admin` to the API on port 8000, so everything is same-origin.

### Database

SQLite is used by default so there's nothing to set up. To use Postgres (with PostGIS and pgvector, needed from WP2), either run `docker compose -f infra/docker-compose.yml up -d` or point at your own server, then set `DATABASE_URL` in `.env` and run `python manage.py migrate`.

## Checks

| | API (`services/api`) | Web (`apps/web`) |
|---|---|---|
| Tests | `pytest` | `npm test` |
| Lint | `ruff check .` | `npm run lint` |
| Format | `ruff format .` | `npm run format` |
| Types | — | `npm run typecheck` |

CI runs all of these on every push, with the API tests against Postgres + PostGIS.

**Assistant evaluations** (real API calls, costs credit): `python manage.py run_evals --live`.
