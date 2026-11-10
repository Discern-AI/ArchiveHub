# Dependencies and licences

**Rule:** no dependency is added without an entry here. Permissive licences (MIT, BSD, Apache-2.0, MPL-2.0, PostgreSQL) may go into the core. GPL/AGPL software is a design reference only, or runs as a separate, unmodified service after legal review (ADR-010, ADR-012). Licences below were noted on 5 Nov 2026 from the source documents; re-check the LICENSE file, maintenance and security advisories when adding each one.

## In use (added as each work package starts)

Filled in as packages are installed. Columns: package · version · licence · purpose · added in.

| Package | Version | Licence | Purpose | WP |
|---|---|---|---|---|
| Django | 5.2.19 | BSD-3 | Backend framework | 1 |
| django-ninja | 1.7.3 | MIT | JSON API | 1 |
| django-allauth[headless] | 65.21.1 | MIT | Accounts for the React app | 1 |
| django-environ | 0.14.0 | MIT | Settings from environment | 1 |
| psycopg[binary] | 3.3.8 | LGPL-3.0 | Postgres driver (unmodified library) | 1 |
| anthropic | 2.5.0 | MIT | Claude API | 1 |
| sentry-sdk | 2.73.0 | MIT | Error monitoring (off unless `SENTRY_DSN` set) | 1 |
| uvicorn | 0.54.0 | BSD-3 | ASGI server | 1 |
| django-rq | 4.2.0 | BSD-2 | Background jobs (installed; used from WP2) | 1 |
| ruff, pytest, pytest-django, pytest-asyncio, factory-boy | — | MIT / MIT / BSD-3 / Apache-2.0 / MIT | Dev: lint, tests | 1 |
| react, react-dom | 18.3.1 | MIT | Frontend | 1 |
| react-router | 7.18.5 | MIT | Routing | 1 |
| @tanstack/react-query | 5.106.1 | MIT | Server state | 1 |
| vite, @vitejs/plugin-react | 8.3.6, 6.2.1 | MIT | Dev: build | 1 |
| typescript | 6.0.3 | Apache-2.0 | Dev: types | 1 |
| tailwindcss, @tailwindcss/vite | 4.3.4 | MIT | Styling | 1 |
| vitest, jsdom, @testing-library/* | — | MIT | Dev: tests | 1 |
| eslint, typescript-eslint, eslint-plugin-react-hooks, prettier | — | MIT | Dev: lint/format | 1 |
| truststore | 0.10.5 | MIT | TLS verification via the OS trust store (ADR-022) | 3 |
| pypdf | 6.21.4 | BSD-3 | PDF text layers and page counts | 4 |
| defusedxml | 0.7.1 | PSF | Safe parsing of Word documents | 4 |
| Pillow | 13.0.0 | MIT-CMU (HPND) | Image checks, previews, EXIF removal | 4 |
| Tesseract (optional binary) | — | Apache-2.0 | OCR when installed; not installed yet | 4 |
| channels | 4.3.2 | BSD-3 | WebSockets for live interviews | 5 |
| websockets | 17.4 | BSD-3 | WebSocket protocol for uvicorn | 5 |
| daphne (dev) | 4.2.3 | BSD-3 | Needed by Channels' test helpers only | 5 |
| faster-whisper (optional, `requirements-speech.txt`) | 1.2.1 | MIT | Speech-to-text for interviews (ADR-028) | 5 |
| ctranslate2, onnxruntime, numpy, tokenizers, huggingface-hub | 4.8.5, 1.31.1, 2.5.4, 0.23.3, 2.4.0 | MIT, MIT, BSD-3, Apache-2.0, Apache-2.0 | faster-whisper's runtime | 5 |
| av (PyAV) | 19.0.2 | BSD-3; its wheels bundle FFmpeg (LGPL) — **check** the bundled build before production | Audio decoding for faster-whisper (spike only; live audio is raw PCM) | 5 |
| Systran faster-whisper small.en / base.en (model weights) | — | MIT (converted from OpenAI Whisper, MIT) | Downloaded from Hugging Face on first use | 5 |
| GB1900 final raw gazetteer data dump (data) | July 2018 | CC0 1.0 | Hosted "Old map names" dataset; must not be named GB1900 (ADR-021) | 3 |
| postgis/postgis image + postgresql-16-pgvector | 16-3.5 | GPL-2.0 (PostGIS, separate service) / PostgreSQL | Dev/CI database | 1 |
| valkey image | 8 | BSD-3 | Dev job queue | 1 |
| maplibre-gl | 6.14.0 | BSD-3 | Time map (loaded only on the map page) | 6 |
| @tanstack/react-virtual | 3.14.23 | MIT | Lifeline rows: only the visible people are drawn | 9 |
| OpenFreeMap tiles (service, `liberty` style) | — | Data ODbL (© OpenStreetMap contributors), OpenMapTiles schema; free, commercial use allowed, no key (checked 2026-11-06) | Modern base map on the time map (ADR-031) | 6 |
| NLS historic OS maps via MapTiler (service) | — | CC BY 3.0, attribution to the National Library of Scotland with a link; MapTiler's free plan is non-commercial and up to 100,000 tiles a month, so a paid plan is needed before launch (checked 2026-11-06) | Historic map layers, only when `MAPTILER_KEY` is set (ADR-031) | 6 |

**Known advisories (5 Nov 2026):** `npm audit` reports 10 moderate advisories in ESLint's dependency chain (`minimatch`), dev-only; production dependencies report none. Fixing needs a breaking ESLint change — revisit when typescript-eslint updates.

## Planned — core stack

| Component | Licence | Purpose |
|---|---|---|
| Django 5 | BSD-3 | Backend framework |
| Django Ninja | MIT | Typed JSON API |
| django-allauth | MIT | Accounts, OIDC/social login |
| django-storages | BSD-3 | R2/S3 file storage |
| django-rq / RQ | BSD-2 / BSD-2 | Background jobs |
| Django Channels | BSD-3 | WebSockets (WP5) |
| psycopg 3 | LGPL-3.0 | Postgres driver (dynamically linked library; standard in Django projects) |
| PostgreSQL 16 | PostgreSQL | Database |
| PostGIS | GPL-2.0 | Spatial extension — runs as a separate database extension, not linked into our code |
| pgvector | PostgreSQL | Vector search |
| Redis | RSALv2/SSPL (7.4+) — check; or Valkey (BSD-3) | Job queue. Prefer Valkey if Redis licence is a concern |
| anthropic (Python SDK) | MIT | Reasoning AI |
| sentry-sdk | MIT | Monitoring |
| React 18, React DOM | MIT | Frontend |
| Vite, @vitejs/plugin-react | MIT | Frontend build |
| TypeScript | Apache-2.0 | Frontend language |
| Tailwind CSS | MIT | Styling |
| TanStack Query | MIT | Server state |
| React Router | MIT | Routing |
| Ruff, pytest, pytest-django | MIT, MIT, BSD-3 | Python lint/format/tests |
| ESLint, Prettier, Vitest | MIT | Frontend lint/format/tests |

## Use first (from the source documents)

| Repo | Use | Area | Licence |
|---|---|---|---|
| [Topola](https://github.com/PeWu/topola) / [Topola Viewer](https://github.com/PeWu/topola-viewer) | Display GEDCOM trees | Record | Apache-2.0 |
| [family-chart](https://github.com/donatso/family-chart) | Embeddable, editable tree | Record | MIT |
| [FamilySearch GEDCOM](https://github.com/FamilySearch/GEDCOM) | Import/export standard | Record | Apache-2.0 |

## Add when needed

| Repo | Use | Area | Licence |
|---|---|---|---|
| [GEDCOM X](https://github.com/FamilySearch/gedcomx) | Exchange model reference | Record, Research | Apache-2.0 |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Transcription | Record | MIT |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Alternative transcription | Record | MIT |
| [openai/whisper](https://github.com/openai/whisper) | Transcription baseline | Record | MIT |
| [Docling](https://github.com/docling-project/docling) | PDF/Office text extraction | Record | MIT |
| [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) | Searchable scanned PDFs | Record | MPL-2.0 |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) | Printed-text OCR | Record | Apache-2.0 |
| [docTR](https://github.com/mindee/doctr) | OCR pipeline evaluation | Record | Apache-2.0 |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | OCR/layout evaluation | Record | Apache-2.0 |
| [Kraken](https://github.com/mittagessen/kraken) | Historical handwriting | Record, Research | Apache-2.0 |
| [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) | Time map and service map | Research, Connect | BSD-3 |
| [TanStack Table](https://github.com/TanStack/table) | Explorer tables | Research | MIT |
| [TanStack Virtual](https://github.com/TanStack/virtual) | Very large lists | Research | MIT |
| [Archival IIIF Viewer](https://github.com/archival-IIIF/viewer) | Mixed archive media | Research, Home | MIT |
| [Mirador](https://github.com/ProjectMirador/mirador) | Compare archive images | Research, Home | Apache-2.0 |
| [OpenSeadragon](https://github.com/openseadragon/openseadragon) | Zoom large scans | Record, Home | BSD-3 |
| [Universal Viewer](https://github.com/UniversalViewer/universalviewer) | Alternative IIIF viewer | Research, Home | MIT |
| [ArchiveBox](https://github.com/ArchiveBox/ArchiveBox) | Capture old sites before migrating | Home | MIT |
| [internetarchive (Python)](https://github.com/jjjake/internetarchive) | Internet Archive API | Research | AGPL-3.0 — **check**; call the HTTP API directly instead if so |
| [OpenSearch](https://github.com/opensearch-project/OpenSearch) | Only if Postgres search can't cope | Research | Apache-2.0 |
| [Apache AGE](https://github.com/apache/age) | Only if graph queries get hard | Shared | Apache-2.0 |
| [MapReader](https://github.com/maps-as-data/MapReader) | Features from scanned maps | Research | MIT |
| [Allmaps](https://github.com/allmaps/allmaps) | Align old maps with modern | Research | No root licence found — check |
| [OpenRefine](https://github.com/OpenRefine/OpenRefine) | Clean partner datasets internally | Research | BSD-3 |
| [Heritrix](https://github.com/internetarchive/heritrix3) | Capture larger authorised sites | Home | Apache-2.0 |
| [Ghost](https://github.com/TryGhost/Ghost) | If publishing outgrows the built-in blog | Home | MIT |
| [Cal.com](https://github.com/calcom/cal.com) | Full booking; check paid-only parts | Connect | MIT file (mixed) |
| [defoe](https://github.com/defoe-code/defoe), Reading the Unreadable | Study newspaper OCR/text analysis | Research | MIT |

## Reference only — copyleft; study, or run separately after legal review

| Repo | Why it's useful | Licence |
|---|---|---|
| [Gramps Web](https://github.com/gramps-project/gramps-web) / [API](https://github.com/gramps-project/gramps-web-api) | Strong genealogy model | AGPL-3.0 |
| [Gramps](https://github.com/gramps-project/gramps) | People/events/places/sources reference | GPL |
| [webtrees](https://github.com/fisharebest/webtrees) | Collaborative tree and privacy ideas | GPL |
| [GeneWeb](https://github.com/geneweb/geneweb) | Large-tree logic | GPL |
| [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) | Document ingestion | GPL |
| [Tropy](https://github.com/tropy/tropy) | Research photo management | AGPL |
| [Immich](https://github.com/immich-app/immich) | Photo library (leave face recognition out) | AGPL |
| [CollectiveAccess](https://github.com/collectiveaccess/providence) / Pawtucket2 | Institutional cataloguing | GPL |
| [Omeka S](https://github.com/omeka/omeka-s) | Exhibitions, linked data | GPL-3.0 |
| [AtoM](https://github.com/artefactual/atom) | Standards-based description | AGPL |
| [Archivematica](https://github.com/artefactual/archivematica) | Preservation workflow | AGPL |
| [ArchivesSpace](https://github.com/archivesspace/archivesspace) | Archive management | ECL-2.0 |
| [Browsertrix Crawler](https://github.com/webrecorder/browsertrix-crawler) / [pywb](https://github.com/webrecorder/pywb) | Web archive capture/replay | AGPL / GPL |
| [BookReader](https://github.com/internetarchive/bookreader) | Digitised books | AGPL |
| [WordPress Importer](https://github.com/WordPress/wordpress-importer) | Learn WXR, then write our own | GPL |
| [Discourse](https://github.com/discourse/discourse) | Forums as a connected service | GPL |
| [Lemmy](https://github.com/LemmyNet/lemmy) | Reddit-style forum reference | AGPL |
| [Postiz](https://github.com/gitroomhq/postiz-app) | Social scheduling reference | AGPL |
| [MinIO](https://github.com/minio/minio) | S3 emulator — not used (ADR-012) | AGPL-3.0 |
| [Mastodon](https://github.com/mastodon/mastodon) | Federation patterns | AGPL |
| [FreeUKGen MyopicVicar](https://github.com/FreeUKGen/MyopicVicar) | Volunteer transcription platform (code, not data) | Apache-2.0 |
