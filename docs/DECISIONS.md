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

## ADR-028 — Speech on our own server first, behind an adapter
**Status:** Provisional · 2026-11-05 (to be confirmed by the speech spike with real recordings)
Interview audio is transcribed by faster-whisper (MIT) on our own server, behind a provider adapter (`interviews/speech.py`) so a hosted speech API can be added if the spike favours it. Reasons: family recordings never leave our server, there is no per-minute charge, and no extra processor needs adding to the privacy notice. Finished lines use `small.en`; provisional live words use the faster `base.en` so they keep up with the speaker. On a laptop CPU, live words trail speech by about 1–2 s and finished lines arrive about 4–5 s after a pause; a GPU server or a hosted API would cut that. `python manage.py speech_spike` measures accuracy (WER), line delay and cost on consented recordings, including British accents and older speakers. The decision is confirmed or reversed on those results, not on synthetic speech.

## ADR-029 — Live interviews: raw audio over a WebSocket, lines found by pauses
**Status:** Accepted · 2026-11-05
The browser captures the microphone with an AudioWorklet and sends 16 kHz mono 16-bit PCM over a Django Channels WebSocket (`/ws/interviews/<id>`), authenticated by the session cookie and limited to our own origins. The server keeps every byte in a WAV file (the original, with a SHA-256), finds the end of each line with an energy-based pause detector, and transcribes each finished line. Nothing is recorded or sent while paused. If the connection drops, the recording so far is kept and can still be sent. People, places, dates and follow-up questions are picked up in the background with Claude and shown only in the side panel; they are interpretation, stored separately and linked to transcript lines, and they never interrupt the speaker. If they fail (for example, no API credit), the transcript carries on. "End and send" writes the transcript into the chat (as marked data for the assistant) and a response whose line citations are resolved by the server (ADR-020). A failed response is not saved, so it never enters the chat history, and can be retried. Consent is recorded per interview: who confirmed it, when, and the exact notice shown.

## ADR-030 — Locations stay as latitude/longitude; PostGIS waits for shapes
**Status:** Accepted · 2026-11-06 · decided by the owner · supersedes ADR-019's plan to migrate in WP6
**Considered:** GeoDjango with PostGIS geometry now (as ADR-019 planned), or keep latitude/longitude columns.
**Decision:** Places and map items keep latitude/longitude with a precision and a source for every location (`Place.geocode_source`). The time map asks for an area with indexed bounding-box queries, which work on SQLite and Postgres alike.
**Why:** GeoDjango needs GDAL on every development machine and stops the default SQLite setup from working. The time map only needs points in a rectangle, which plain indexes handle at pilot scale. PostGIS (ADR-004) is still the plan for shapes: coverage areas in Connect (WP8), parish boundaries and historic street lines. Move then, or when point queries are measured to be slow.

## ADR-031 — Time map layers: OpenFreeMap today, NLS historic maps behind a key
**Status:** Accepted · 2026-11-06 · decided by the owner
**Considered:** openstreetmap.org's own tiles (their policy warns commercial users that access can be withdrawn at any time and forbids heavy use), OpenFreeMap, NLS historic maps through MapTiler, and no historic tiles yet.
**Decision:** MapLibre GL JS with OpenFreeMap's vector "liberty" style for today (free, commercial use allowed, no key; OpenStreetMap attribution shown on the map). Historic OS maps from the National Library of Scotland (six-inch 1888–1913, 1920s–1940s, 1:25,000 1937–1961) through MapTiler, switched on only when `MAPTILER_KEY` is set; without it, historic layers are listed as unavailable rather than hidden. NLS attribution and the CC BY 3.0 link are always shown with a historic layer.
**Why:** CC BY 3.0 allows commercial use with attribution, but MapTiler's free plan is non-commercial, so the pilot can use the free plan and a paid plan is needed before launch (owner action). MapTiler keys are visible in the browser by design; restrict the key to our own sites in MapTiler. The c.1900 old map names (ADR-021) appear as labels for c.1888–1913 even without historic tiles. Other historic layers (OpenHistoricalMap, Allmaps alignments of local maps) need their terms checked first.

## ADR-032 — The time map's public and private layers
**Status:** Accepted · 2026-11-06
Public: shared checked records and claims about places, pubs and businesses at a placed location, shared events that name no people, and old map names. Private: a project's map items (memories, photos, documents, interview passages) and project claims, shown only to people who can see that project. Each item is tagged with its layer by the server, and the map draws them differently (round public pins, square private pins marked "Private") and lists them separately. Claims about people are not mapped yet, so living people can't be located through the map (ADR-015). Each item's date says what kind it is: when something happened, when a photo or document was made, the years a record covers, or the map survey's years. Undated items appear only when asked for. A street-level location is labelled as such; we don't place an item more precisely than its source allows.

## ADR-033 — Search: one permission-checked endpoint, word matching first
**Status:** Accepted · 2026-11-06
`GET /search` looks in places, pubs and organisations, checked records, old map names and the source directory (public), and in the person's map items, Archive files (names and text read from them), interview transcripts and family-tree people (private, only from projects and chats they can see). Each group says what was searched; a fixed list says what wasn't (forums and the services directory until WP8, live sources searched one at a time in the Explorer, link-out-only sources). Matching requires every word to appear in one of a group's fields, which works the same on SQLite and Postgres. Postgres full-text ranking and pgvector (ADR-004) come when hosted datasets outgrow this; the response shape won't change. Search never charges credits (SPEC §12, Charges).

## ADR-034 — Live connectors that need keys: built now, switched on per key
**Status:** Accepted · 2026-11-07 · requested by the owner
**Decision:** Connectors for Europeana, The National Archives' Discovery, Geograph, OS Names, DigitalNZ, Trove and DPLA share one base (`connectors/live.py`). Each reads its key from settings. Without it, the source appears in the Explorer under "not available here yet", with what's needed, and every search says it "isn't set up on this server yet" without making a request. FamilySearch is not built: its API is closed to the public and production access needs an approved partner application.
**Rules carried into code:**
- What may be kept follows each source's terms (`storage`). TNA Discovery's terms forbid caching or storing anything it returns, so its results are used for the current answer only: the saved chat history keeps a note instead of the results, and the Research Basket and citations keep only the record's ID and link. TNA asks for at most one request a second, which the connector enforces. Answer text the assistant writes from TNA results is still saved with the chat; confirm this with TNA when access is approved.
- Keys travel in headers where the API allows (Trove, DigitalNZ). Error messages never include request URLs, so keys can't leak into logs or "What I checked".
- Live sources receive the search words. The assistant is told never to send names of living people or private details from users' files, and that a name match is a possible match, not the same person.
- Commercial terms differ: Europeana needs a project key; Trove needs the National Library of Australia's explicit permission; DigitalNZ allows commercial use only with a key and only for selected metadata; Geograph forbids bulk collection through the live API. See `docs/CONNECTORS.md`.
**Tested:** Europeana (with its public demo key), TNA Discovery, DigitalNZ and Geograph were run against the real services on 7 Nov 2026, and the tests replay trimmed real responses. Trove, DPLA and OS Names follow their documented formats and haven't been run against the live services yet.

## ADR-035 — Historic England, The Gazette and GeoNames connectors
**Status:** Accepted · 2026-11-07 · requested by the owner
**Decision:** Three more live connectors on the ADR-034 base. **National Heritage List for England** (Historic England's open ArcGIS service, OGL, no key): listed buildings with grade, listing date and exact location. A town named in the query (one we can locate from our places or the c.1900 map names) becomes a search area; only letters and digits reach the service's query. **The Gazette** (OGL, no key): searched only up to the end of the year 100 years ago, because recent notices (deceased estates, insolvencies) name living people and their addresses, and the OGL doesn't cover personal data (ADR-015). Its fair use policy (5 requests every 10 seconds) is enforced as one request every 2 seconds, and opening a record builds the link without fetching anything. **GeoNames** (CC BY, commercial use allowed): needs a free account name (`GEONAMES_USERNAME`).
**Not built, and why:** World Historical Gazetteer (default licence CC BY-NC); Library of Congress (its API served our server a bot challenge on 7 Nov 2026); Archaeology Data Service (no general search API, only SPARQL); Transkribus (a paid processing service, not a source). Recorded in `docs/SOURCE_REGISTER.md`.
**Note:** a listing date is not a build date. Anything shown on the time map from the Heritage List must say "listed in", not "built in".

## ADR-036 — Museums and research connectors; the wider context register
**Status:** Accepted · 2026-11-07 · requested by the owner
**Decision:** Three more open connectors: The Metropolitan Museum of Art and the Art Institute of Chicago (CC0 data; images only for public-domain objects; the Art Institute's CC BY descriptions aren't fetched), and OpenAlex (CC0 scholarly metadata; works without a key on a small shared budget, `OPENALEX_API_KEY` for production). They are context, not family evidence, and the assistant is told so.
**Not built, and why:** Open Library (its API is "not intended for high-traffic commercial infrastructure"), UK PlanIt (commercial use not addressed; planning documents are copyright), HM Land Registry Price Paid (address data may only be displayed for property price information services; legal check first), V&A (terms section couldn't be read), Planning Data England (service down when tested), Portable Antiquities Scheme and Open Domesday (no licence stated). All are in `docs/SOURCE_REGISTER.md`, with the key-needing APIs listed in its section 5 and the wider context sources in section 10.
**Rule for wider context:** statistics, modelled weather, museum objects and other people's testimony describe a period. They are never presented as facts about a particular person.

## ADR-037 — Outside sources in Search are opt-in; listed buildings on the time map
**Status:** Accepted · 2026-11-07
**Search:** a checkbox, "Also search outside sources", asks every set-up live source that answers in one request (The Gazette, Historic England, TNA Discovery, OpenAlex, Europeana, Wikidata, Geograph, DigitalNZ, Trove, DPLA), five results each, all at once with a 12-second limit. It's off by default because the search words leave our server; the page says so and asks people to leave out living people's names. Each outside group is labelled "Searched live"; a source that fails or is slow says so, sources not set up are listed under "Not searched", and live results are never saved. The museum connectors aren't included because each result costs a request.
**Time map:** a "Listed buildings" layer (on by default) draws listed buildings from Historic England's live service for areas about the size of a town centre, cached for a day (the list is updated daily, OGL). They show for every year, since a listing date isn't a build date, and both the panel and the record say so. Brown "L" pins keep them apart from records (green circles) and private items (purple squares).

## ADR-038 — Family trees on the time map: suggested places a person checks
**Status:** Accepted · 2026-11-07
Places in a family tree are text. "Find locations" suggests where each one is, from the first source that knows it: our own places, then the c.1900 map names (settlement labels in capitals), then GeoNames when it's set up. Each suggestion keeps its source and precision; if several far-apart places share the name it says so. Only the place name is ever sent out. A project editor marks each one right or wrong, or places it by clicking the map; their decision is never overwritten by a later lookup. Births, baptisms, deaths and burials then appear as private "F" pins for the project, with the place as written and "location suggested, not yet checked" until confirmed. People counted as living (including unknown, ADR-025) never appear on the map, even privately.

## ADR-039 — Protected areas on the map; checked explanations of old terms
**Status:** Accepted · 2026-11-07
**Protected areas:** conservation areas, scheduled monuments, registered parks and gardens and battlefields come live from Historic England's open ArcGIS services (OGL), as outlines coloured by kind with a popup and link, cached for a day. Like listed buildings they show for every year, with the designation year. A layer that fails says so and isn't cached.
**Explanations:** `history/data/glossary.json` holds explanations written in our own words, each checked on 7 Nov 2026 against a named page: old money (University of Nottingham, Manuscripts and Special Collections), Poor Law terms (The National Archives' "Poverty and the Poor Laws" guide) and 36 Ordnance Survey abbreviations (the National Library of Scotland's list, compiled by Dr Richard Oliver). Abbreviations often have several meanings ("P" is pump, post, pillar…), so every meaning is shown with "could be", never one guessed answer; this replaces the single meanings first used in "What else is known here?". The assistant's `explain_term` tool cites them; Search shows them as "Explanations of old terms". New entries need the same check (ADR-018). An explanation describes the period, never a particular person.

## ADR-040 — Tree health check and GEDCOM import report; Gramps stays a reference
**Status:** Accepted · 2026-11-07
**Health check:** "Check this tree" lists things worth a second look, using the facts currently in use (corrections win over imports): impossible or unusual dates, parents under 13 or unusually old (mothers over 55, fathers over 80), births after a parent's death (allowing about a year after a father's), possible duplicates (same name, births within two years), separate branches and people with no dates. Findings are prompts, never errors: nothing is changed, hidden or merged (ADR-005, "never auto-merge people").
**Import report:** every GEDCOM import records what came across and what didn't (source citations, source records, notes, media references and facts such as residences), shown on the file's page. Media in GEDCOM files are usually references, so people are told to upload the files separately. The original file is never changed.
**Considered and declined:** a suggestion to use the Gramps Web API as the genealogy engine. It's AGPL, so it stays a design reference (ADR-010); our importer and the health check cover the first needs, and GEDCOM 7 export plus GedZip media bundles are the next steps.
**Record sources:** the review of where records really come from (archives license non-exclusively to commercial sites) is in SOURCE_REGISTER.md §11, with Free UK Genealogy and the UK Data Service added to the outreach list.

## ADR-041 — "Where to look next": a record-finding guide from checked guidance
**Status:** Accepted · 2026-11-10
For a person who has died, ArchiveHub lists the records that could exist (civil registration, parish registers, each census in their lifetime, the 1939 Register, service records, probate), who holds them, whether they're free, paid or visit-only, and the cost, on the person's page and as the assistant's `where_to_look` tool. Rules come from guidance checked on 10 Nov 2026: civil registration from 1 July 1837 (England and Wales) and 1 January 1855 (Scotland); the GRO's free historical index (births over 100 years old, deaths 1837–1957; image about £3, PDF about £8); census years 1841–1921, free at Kew, 1921 free at Manchester and the National Library of Wales, 1931 destroyed in 1942 and none in 1941; the 1939 Register; probate copies from 1858 at £16 online; Scottish online image cut-offs (100/75/50 years); MOD service record fees since 2 Feb 2026. Routes not yet checked (CWGC, Scottish parish registers and census, wills before 1858) are shown as leads and labelled. It says where a record would be, never that one exists. People who may be living get no suggestions. Royal Berkshire Archives is named for Berkshire places; elsewhere "the county record office".
