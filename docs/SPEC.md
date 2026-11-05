# ArchiveHub — Product and Build Specification (merged)

**Version:** 1.0 merged · **Date:** 5 November 2026 · **Owner:** Adam Belcher

This is the single source of truth for building ArchiveHub. It merges two inputs:

- **Spec** — *ArchiveHub Product and Build Specification* (25 pages plus a React/Vite prototype appendix).
- **Blueprint** — *ArchiveHub Master Product, Research, Architecture and Development Blueprint* v1.0.

Originals go in [`docs/sources/`](sources/). Where the two disagreed, the choice made and its reason are recorded in [`DECISIONS.md`](DECISIONS.md). Data sources live in [`DATA_SOURCES.md`](DATA_SOURCES.md) and third-party code in [`DEPENDENCIES.md`](DEPENDENCIES.md).

Nothing here claims that an integration, licence or partnership has been secured.

---

## 1. Summary and vision

ArchiveHub is a chat-first platform where people preserve family and local history, research the past, publish their work and find the people who can help. It is built first around one place, **Newbury and West Berkshire**, to prove that people will keep adding material before pursuing national data deals.

The long-term vision is a connected historical record of Britain. A person links to a street, the street to a building, and the building to photographs, directories, newspapers, films and memories. Every link keeps its source, its evidence status and its owner's permissions. A record should be discoverable by **who, what, where and when**.

### The product's edge

1. **Private memory:** interviews, letters, photos and family knowledge that exist in no commercial record set.
2. **Evidence you can inspect:** documented, remembered, inferred and disputed claims stay separate; conflicts stay visible.
3. **A home for local historians:** cheap hosting, publishing and ways to be found, while they keep ownership and can leave at any time.
4. **A guide to the archival world:** a curated source directory, so the assistant knows what exists and where to look even when it can't access the record.
5. **A connector network:** one interface over sources held by many organisations, federating before copying.
6. **A credible return for contributors** who preserve historical material.

### Working assumptions

- ArchiveHub is a working title.
- Launch market: UK, starting in West Berkshire.
- Status: concept with a clickable prototype; no production code yet.
- Facial recognition, and automatic face matching of people across archives, is out of scope. Revisiting it needs its own legal review and opt-in process.

## 2. Principles

- **Chat-first, not chat-only.** Conversation opens real visual editors and navigable records.
- **Browse without AI.** People can spend an afternoon paging through records without prompting the assistant.
- **Evidence before narrative.** Scans and metadata are primary; AI prose is derivative and cited.
- **Uncertainty is a feature.** Contradictory claims stay distinct until a person decides.
- **Private by default.** Uploading never implies publishing or permission to train models.
- **No automatic rights.** Hosting someone's archive does not assign copyright, database rights or licences.
- **Portable.** GEDCOM, CSV, JSON, IIIF, metadata and full site export; people can always leave.
- **Federate first, copy only where licensed.**
- **Accessible by design.** Keyboard navigation, screen-reader labels, transcripts, non-chat routes for every task, mobile layouts, reduced-motion support. Include older users in testing.
- **Understandable costs.** Storage, AI credits, partner fees and support for contributors are shown separately; no surprise charges.
- **Archival durability.** Originals, checksums, revision history, stable IDs and an export path.

## 3. The four user areas

The areas are things people do, not account types. One account can record a family, research a pub, publish a blog and take bookings in the same week, on the same data.

| Area | Who it's for | First version | Later |
|---|---|---|---|
| **Record** | Families and enthusiasts | Chat, Archive (files), GEDCOM import/export, guided interviews, family pages | Family collaboration, handwriting correction, deeper video processing |
| **Research** | Anyone looking for a person, place or event | Source directory, research guide, Archive Explorer, evidence panel, research basket | More licensed data, cross-database matching, knowledge-graph navigation |
| **Home** | Historians, bloggers, societies, small organisations | Homepage, posts, gallery, collections, publish-from-chat with approval, migration help | Direct posting to other sites, memberships, digital sales, custom domains |
| **Connect** | Speakers, researchers, archivists and people looking for them | Profiles, directory, map search, enquiries, tips, moderation | Forums at scale, full bookings, paid research requests, marketplace payments |

**How they feed each other:** someone recording their family hits a wall and turns to Research. Research points them to a local historian's work. That historian gets a tip or booking, and their public archive brings in new people.

**Build order:** Research → Record → Home → Connect. Research is cheapest and doesn't need people to trust us with files. Record creates the unique private material and credit revenue. Move 3–5 historians across by hand before automating Home. Connect needs enough people and profiles to be useful.

### 3.1 Record — detail

- People, households, relationships, events, alternative names; GEDCOM 7 import/export (5.5.1 compatibility where the parser allows).
- Archive: folders, drag-and-drop, tags, previews, bulk actions, share links, storage meter.
- Photos, scans, audio, video, letters, diaries, certificates, clippings.
- Oral-history interviews with consent metadata, speaker labels and follow-up questions.
- Timelines built from cited records and attributed testimony.
- Corrections, conflicting evidence, confidence and version history.
- Invite relatives with granular roles; living people restricted.
- Publish only selected narratives, media or records.

### 3.2 Research — detail

- Source directory searchable by place, period, format, holder, price, access method and licence.
- Search across connected data, always stating what was and wasn't searched.
- Archive Explorer (§5), research baskets, saved searches, comparisons, notebooks.
- Address histories, historic place-name variants, period maps.
- Hypothesis tracking and incomplete-answer notices.
- "Surprise me" random discovery by place, period and type.

### 3.3 Home — detail

- Personal or organisation profile, posts, galleries, exhibit pages, collections. Historian, society and family pages are variants of one system.
- Draft from chat → preview in the right panel → explicit approval → publish.
- Pre-publish check: flag living people, private files and unclear image rights.
- Destinations: ArchiveHub homepage, a connected existing blog, prepared social posts. When a post appears twice, one is marked as the original.
- Migration: import WordPress (WXR) and static sites, keep old links working via redirects, full export at any time.

### 3.4 Connect — detail

- Directory of historians, researchers, archivists, societies and services, with topics, area, period and availability. The map shows each listing's coverage area.
- Enquiries, tips, then bookings and paid requests.
- Topic forums (brick walls, photo identification, pubs and breweries, military records, local areas, research methods). Posts can be drafted in chat and approved before going live. Reporting, moderation, block lists and clear rules come before forums open.
- Collaborative transcription and volunteer projects with attribution.

## 4. Interface

Chat is how people start almost everything; a right-hand workspace shows what chat can't: trees, sources, previews, databases. The prototype (`prototype-reference/`) is the visual reference — keep its dark green visual language, centre chat, sidebar and contextual right panel unless usability tests show a problem. Its scripted replies and sample data are **not** backend behaviour.

### Layout

- **Top bar:** Search, Map, Forums, Archive; Account menu with Homepage, Profile, Settings.
- **Left panel:** New chat, Projects, Chats.
- **Centre:** the conversation, with one composer for typing, speaking and attaching files.
- **Right panel:** evidence, drafts, trees, interview prompts, previews and the Archive Explorer. Collapsible, resizable, can go full-screen; tabs for several collections, records and a compare view.
- **Phone:** the right panel becomes its own screen; the left panel collapses behind a menu.

Chat navigation, file navigation and the Explorer are independent: the Explorer can open from a result card or an assistant tool call without losing chat state.

### New chat

Four prompts that can be clicked or ignored:

1. Record your family or local history.
2. Research a person, place or event.
3. Are you a historian, archivist or blogger?
4. Is this for your business or services?

They disappear after the first message. For returning users they become suggestions such as "Continue with Alice's timeline". Users never choose an account type.

### Live guided interview (signature Record experience)

1. Pressing the microphone starts an interview. A recording notice reminds the user to tell anyone else who's speaking, and consent is recorded.
2. Words appear live in the bottom bar, which stays in place.
3. After a sentence or two, the words lift from the bar, fade as they rise and settle into the chat. Respect reduced motion.
4. The assistant processes each finished sentence in the background.
5. The right panel shows questions, plus the people, places and dates picked up.
6. The user can answer a question, ignore them or pause. Prompts never interrupt the speaker.
7. **End and send** returns a response and any open questions.

The original audio and full transcript are always kept and linked; AI interpretation never replaces the evidence.

### Archive (files)

Folders, drag-and-drop, previews, upload into chat, storage meter. Everything private unless explicitly published. Basic text and metadata indexing on upload. Handwriting, video and full-collection analysis use credits: show an estimate and ask before starting.

### Evidence panel

A disputed claim opens its sources side by side: what each says, its type, a suggested weight and a link.

- Choices: use one source, keep it disputed, add a reason.
- "Accept" means *use it in this project*, not *it is true*.
- Nothing is lost: rejected sources stay on file with the reason.
- Simple by default: "two sources disagree", full comparison one click away.
- AI is labelled: suggested weights and inferred links are never shown as facts.

### Time map

Choose a place, slide through the years, and see records, photos, film, memories and events tied to it. Public records and private items are visibly separate. Start with Cheap Street and central Newbury. Show today alongside a chosen year. Distinguish an event's date from a document's publication date. Historic narratives (e.g. a writer's walk) need a traceable source; don't assert a precise route where the text gives only a town.

### Search

Covers records, photos, places, forum threads, and people and services. Every search states what was searched and what wasn't, so an empty result is never mistaken for proof that something doesn't exist.

### Trust signals

Every source card shows its identity, access status, last fetched/indexed time, record type, rights and what was actually searched (metadata, full text or original). Answers distinguish *evidence found*, *possible match*, *not searched*, *no accessible match* and *requires external access*.

### Confirmations

Publishing, deleting, changing sharing, sending external posts, taking payments and spending credits on large jobs always need an explicit user action.

## 5. Archive Explorer

People open a database in the side panel and search, filter or simply browse. Purposeful research and exploratory browsing matter equally, and it must work without the assistant.

- **One browser, many sources:** the same interface for every connector.
- **Access labels:** each source says whether it's hosted here, searched live, metadata only or link-out (§8).
- **Views:** virtualised table (server-side cursor paging over millions of rows), record detail with next/previous, photo grid, document/IIIF viewer, map, timeline, related records (similarity is never identity).
- **Research Basket:** saves records to a project as a full copy or a reference and link, according to the source's storage policy.
- **Works with chat:** a selected record passes its structured fields and source to the assistant — never raw HTML.
- **Compare:** two databases or records side by side.
- **Surprise Me:** a random record from a defined, accessible corpus, by area, period and type, with a reproducible reference.
- **Database directory:** every known source, including those that can't be connected.
- **Controls:** dataset, provider, collection, period, place, record type, access tier, filters, sort, save, annotate, compare, export where allowed, ask assistant, open original, citation, support source, report metadata error.

Example: a user opens Berkshire parish registers, filters to Speen, opens a marriage, saves it, switches to a census index and asks "could this be the same household?". The assistant gets both structured records with provenance, gives a provisional comparison, never merges people automatically, and links back to both originals.

## 6. Assistant behaviour

1. Answer from retrieved sources, and link them.
2. Separate documented, remembered, inferred and disputed claims.
3. Say what was searched, what couldn't be accessed and what to try next ("What I checked" block).
4. Never invent records, dates, people, quotes or links. If nothing is found, say so. Distinguish "no search result" from "not present in history".
5. Ask before publishing, deleting, sharing or spending credits on large jobs.
6. Treat user files and web content as untrusted data; instructions found inside documents are never followed.

### Tools

The assistant calls explicit, permission-checked, audited tools and never runs arbitrary SQL or invents citation IDs. Initial set:

`search_archive`, `search_source_directory`, `search_connector`, `query_dataset`, `get_record`, `open_iiif_manifest`, `find_related_entities`, `create_assertion`, `compare_evidence`, `add_to_basket`, `import_gedcom`, `update_tree_suggestion`, `create_timeline`, `transcribe_audio`, `extract_handwriting`, `draft_publication`, `preview_publication`, `request_publish_approval`, `estimate_credit_cost`, `start_processing_job`, `find_service_provider`.

Tools return structured records with source IDs, permissions and warnings.

### Identity resolution

Start with transparent deterministic candidates (name variants, dates, places, relatives) and user review. Probabilistic linkage later, keeping scores and explanations. Merges and unmerges are reversible. Never link people because names and birth years match, and never by biometric face matching.

### AI economics

Cheap extraction on upload; expensive OCR, handwriting, AV processing, bulk extraction and whole-collection analysis only on request and against credits. Cache legitimate deterministic outputs; never put private extracted text into shared indexes. Budget limits per user and organisation.

## 7. Technical architecture

One modular product on one shared database, with specialist tools behind clear service boundaries. ArchiveHub owns master IDs, provenance, permissions and links even when another tool does a specialist job. No separate systems for genealogy, cataloguing, publishing and forums. Background workers are separate processes, not separate services; split out ingestion, public search or media only when measured load warrants it.

```
Chat-first interface (React)
  └─ Assistant + permission-checked tools
       ├─ Record   (Archive, GEDCOM, interviews, OCR)
       ├─ Research (directory, Explorer, evidence, connectors)
       ├─ Home     (homepages, posts, migration, approval)
       └─ Connect  (profiles, listings, forums, payments)
            └─ Shared historical data owned by ArchiveHub
               (people, places, events, sources, assertions, evidence, permissions, usage)
                 ├─ Infrastructure: Postgres + PostGIS + pgvector, Redis jobs, object storage
                 └─ External sources: approved APIs, downloads, link-outs
```

### Stack (see ADR-002 and ADR-003)

| Layer | Choice | Note |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite, Tailwind CSS | Ported from the prototype; design tokens from its palette. TanStack Query for server state |
| Backend | Python 3.12+, Django 5, Django Ninja API | Modular monolith with clear apps; Django admin for curating sources |
| Public pages | Django server-rendered templates | Homepages and posts need SEO and fast loads (WP7) |
| Auth | Django auth + django-allauth | Mature, OIDC/social-ready; no hand-rolled security |
| Database | PostgreSQL 16 + PostGIS + pgvector | Single source of truth, spatial queries, AI search |
| Search | Postgres full-text + pgvector hybrid, with citations | OpenSearch only if Postgres can't cope at hosted-dataset scale |
| Graph | Relational tables first | Apache AGE only if queries demand it |
| Jobs | Redis + RQ | OCR, transcription, imports, connector jobs |
| Files | S3-compatible: Cloudflare R2 in production, local filesystem in dev | Originals unchanged, derivatives stored separately |
| Streaming | Server-sent events for chat (WP1); WebSockets via Django Channels for live interview audio (WP5) | |
| Reasoning AI | Anthropic API behind a provider adapter | Chat, evidence reasoning, drafting; model set by configuration |
| Bulk AI | Mistral or a similar lower-cost model, same adapter | Entity extraction, classification, embeddings |
| Maps | MapLibre GL JS + PostGIS | Time map and service map |
| Hosting | Docker Compose for dev; Railway at first | Review storage and processing costs early |
| Monitoring | Sentry | Errors and failed jobs |
| Payments | A marketplace payment provider | Never hold other people's money directly |

### Django apps

```
accounts/      users, profiles, families, organisations, permissions
projects/      projects, chats, messages, research baskets
archive/       files, folders, versions, previews, processing jobs
interviews/    sessions, audio, transcripts, prompts, extracted items
history/       people, places, addresses, events, sources, assertions, links
genealogy/     GEDCOM import and export, relationships, tree data
research/      source directory, assistant tools, citation handling
connectors/    GB1900, National Archives, Wikidata, Europeana and later sources
explorer/      shared database browser and record views
publishing/    homepages, posts, collections, migration, cross-posting
community/     forums, moderation, reports
services/      listings, coverage areas, enquiries, bookings
billing/       credits, tips, ledgers, statements, contributor payouts
rights/        licences, consent, takedowns, audit log
```

Apps are created when their work package starts, not all up front.

### Repository layout

```
ArchiveHub/
├── CLAUDE.md                project rules for coding assistants
├── docs/                    SPEC, DECISIONS, DATA_SOURCES, DEPENDENCIES, sources/
├── apps/web/                React + TS frontend
├── services/api/            Django project (apps above); RQ workers run from the same codebase
├── fixtures/illustrative/   explicitly synthetic data only
├── infra/                   docker-compose.yml, Dockerfiles
├── prototype-reference/     the original prototype, untouched
└── scripts/
```

### Live transcription

Browser audio → WebSocket → transcription service → sentence detection → background analysis. The first WP5 spike compares faster-whisper with a hosted speech API on accuracy, delay and cost, including British accents and older speakers.

### Ingestion pipeline

`uploaded → scanned (malware, file type) → extracted → indexed → optional enrichment → review ready → available/published`, with retries, idempotency keys, deduplication and cancellation. Formats: PDF, TXT, DOCX, JPG, PNG, TIFF, WEBP, WAV, MP3, MP4, CSV, XLSX, JSON, GEDCOM, WARC, ZIP, with explicit size limits. Safe archive extraction, EXIF privacy handling, checksums on every original. OCR for print, HTR for handwriting, speech-to-text for audio; extraction revisions shown beside the source. Never replace a scan with its OCR or a paraphrase.

### API conventions

Cursor pagination for large datasets. Rights, provenance and per-record availability on every relevant response. Read-only research endpoints separate from mutations. External publication requires approval. Permissions are enforced at the database query, vector retrieval, thumbnail rendering, embedding index, API and citation expansion; a public page must never reveal private evidence it references.

## 8. Data model

### Core objects

| Object | Purpose | Key fields |
|---|---|---|
| `Person` | A person across records | Names, dates, living status, visibility |
| `Place` | A location that changes over time | Names, geometry (PostGIS), valid dates, parent place |
| `Address` | A street address at a point in time | Street, number, valid dates, source |
| `Event` | Birth, move, closure, talk or anything dated | Type, date range, place, people |
| `Organisation` | Pub, business, society, regiment | Names, type, dates |
| `Source` | A database, book, file, website or memory | Holder, licence, access type, URL, citation |
| `SourceRecord` | One entry in a source | Source, stored fields, external ID, access rules, original payload ref |
| `MediaObject` | Original photo, audio, video or scan | File, checksum, derivatives, rights status |
| `Assertion` | A claim about the world | Subject, predicate, value, status, confidence, method (user/AI/import), revision history |
| `AssertionEvidence` | Links a claim to evidence | Assertion, source record, supports/disputes, note |
| `Relationship` | A link between people | Type, evidence, confidence |
| `Decision` | What a project uses | Assertion, chosen value, reason, user, date |
| `Collection` | A group of material | Owner, visibility, licence, contributor terms |
| `Permission` | Who can see or do what | Subject, object, role, expiry |
| `LicenceGrant` | What a source/collection allows | Indexing, thumbnails, full text, AI processing, display, download, redistribution, training, caching, jurisdiction, termination |
| `ResearchBasket` | Saved records per project | Records, copy-or-reference, notes |
| `Publication` | A public page or post | Author, version, destination, approval, original-of |
| `ServiceListing` | Someone's offer | Type, coverage geometry, contact, prices |
| `UsageEvent` | A qualifying use of a source | Source, project, event type, date, dedup key — no private text |
| `LedgerEntry` | Credits and contributor balances | Account, kind, amount (minor units), reason, reference |

**The rule that protects the whole system:** an AI summary never becomes an independent source. Every assertion traces back to a record, file or person.

### Dates and places

Support full, partial, before/after, approximate and interval dates, and keep the original date text (and calendar where relevant). Historic place names and addresses carry explicit validity periods; modern street numbering may not map to historic premises. Every geocode has a precision (`exact`, `street`, `parish`, `inferred`) and a supporting source.

### Evidence chain

```
original asset / provider record
  → extracted text / metadata (with parser/model version)
  → source reference and version
  → proposed entity mentions and assertions
  → reviewed entity links
  → basket, map or tree
  → cited narrative / published page
```

### Visibility

`private`, `shared-with-users`, `organisation`, `public`, `restricted` — independent of tenancy.

### Data status labels (shown in the product)

`confirmed_live_api`, `verified_metadata_service`, `potential_integration`, `external_only`, `downloadable_dataset`, `partner_collection`, `prototype_fixture` (synthetic, never presented as evidence).

## 9. Connectors

All sources use one interface so the Explorer needs no per-source screens.

```python
class SourceConnector:
    capabilities: set[str]   # search, browse, record_detail, full_text, facets,
                             # media_preview, download, bulk_export, store
    access_type: str         # hosted | live_api | metadata | external_only
    licence: LicenceInfo

    def search(self, query, filters, cursor): ...
    def browse(self, filters, sort, cursor): ...
    def get_record(self, external_id): ...
    def citation(self, record): ...
    def storage_policy(self, record): ...   # full_copy | metadata_only | reference_only
```

| Access type | Shown | Backend | Rights note |
|---|---|---|---|
| `hosted` | Full records/files the owner permits | Our index and storage | Internal rights and partner allocation |
| `live_api` | Provider-approved metadata/media | Live API, cache per terms | Quotas, contracts, attribution |
| `metadata` | Catalogue records, permitted thumbnails | OAI-PMH/dumps/search API | No implied rights to assets |
| `external_only` | Description and outbound link | Provider's own site | Never pretend paid content is accessible |

Each connector records: `id, operator, base_url, capabilities, auth_kind, terms_url, licence, rights_review_status, cache_ttl, rate_limit, attribution, availability, last_checked, error_state, contributor_eligible`.

**Source lifecycle:** discovery → rights validation → endpoint test → schema mapping → provenance/access mapping → sandbox → contract tests → partner sign-off if needed → listed → routine health checks. An unavailable source shows a clear disabled state, never invented results.

**Standards notes:** OAI-PMH gives metadata, not scans. IIIF Content Search searches within an object, not across institutions. Wikidata is context, not genealogical proof. Commercial sites may have no redistributable API — link or negotiate; never route around paywalls or scrape against terms. Many sites forbid embedding; use metadata plus an outbound link.

Archival standards to adopt when they solve a real need: Dublin Core, EAD, ISAD(G), PREMIS, METS, IIIF, OAI-PMH, W3C Web Annotation, GEDCOM.

## 10. Business model and contributor payments

Charge for AI work and storage separately. Storage and archive access are kept clearly apart from credits, so records never appear to vanish when credits run out. Don't promise historians income at launch: lead with cheaper hosting, better tools and more readers, and say plainly that earnings aren't guaranteed.

### Pricing to test

| Plan | Test price | Includes |
|---|---|---|
| Free | £0 | Reading, forums, public catalogue, a small tree, limited AI |
| Credits | £20 | AI interviews, transcription, document reading, written histories |
| Family | ~£5–£10/month | More storage, shared access |
| Researcher | TBD | Higher AI/search limits, exports, multiple projects and clients |
| Creator | Free to start | Homepage, blog, profile; platform cut on tips and services |
| Society / Institution | Custom | Group roles, collections, staff accounts, migration, support |
| Partner collections | Provider-set | Explicit price shown before any request |

For comparison, one 2026 guide puts Findmypast at about £12.95–£24.95/month. Don't charge for basic browsing of material its owner offers free.

### Contributor programme (merged — see ADR-009)

Three strands, kept separate in the books and the interface: **contracted share** (owed), **tips and opt-in support** (the user's choice), and the **Community Heritage Fund** (discretionary).

| Phase | What launches |
|---|---|
| 1. Launch | Tips and direct "support" buttons at the moment someone finds something useful; a "this answer used these collections" panel. Usage events are logged from day one. |
| 2. Pilot with 5–10 partners | A **fixed revenue-share pool** (a defined % of revenue, never an uncapped per-use fee) split by qualifying use; monthly statements; minimum payout threshold. |
| 3. Later | **Opt-in per-source micro-support** (1p/5p/10p/custom per qualifying use) with a hard monthly cap the user sets (£1/£5/£10/custom), a visible running balance and an off switch. A **Community Heritage Fund** and open-source sponsorship (e.g. tools we depend on) for work that's valuable but rarely "used". |

**Qualifying use:** saving a record to a project; using a record in a cited AI answer (limited per request); opening a contributor-supported item if its agreement says so. Never: scrolling, seeing a result, refreshing, repeating a search or duplicate tool calls. De-duplicated per user/project/source/time window. Partner agreements can override defaults. Software projects are sponsored, not paid per record.

**Payout rules:** append-only ledger with reversal entries; reconcile against revenue and refunds; batch monthly once a threshold is met; never process pennies as separate payments; use a marketplace payment provider; per-user caps, idempotency and fraud checks against gamed counts. Micro-support is charged with the user's normal subscription or top-up, shown as its own line, never taken from credits silently. Say "tip" or "support", not "donation", unless charity rules are met; never promise Gift Aid.

**Statements** show contributors broad usage and earnings by collection — never a family's private research or inferred interests.

Worked illustration (not a forecast), 100 paying users: 1p per use at one use/day ≈ £30/month; a 5% pool of £20/month ≈ £100/month. If £20 is a one-off purchase the pool is smaller.

### Metrics

Families returning and adding material after week one; interviews completed; research tasks leading to a useful next step; historians migrating or publishing regularly; time to first useful record; citations per answer; wrong-merge rate; connector error rate; credits bought per active user; cost per interview, document and research task; tips/enquiries/bookings sent to contributors; contributor satisfaction; privacy incidents (target zero).

## 11. Rights, privacy and legal checks

Rights decide what the product can do, so they are in the data model from day one. This is a product checklist, not legal advice; a lawyer or specialist reviews it before launch.

| Area | Rule to build | Check with a specialist |
|---|---|---|
| User uploads | Private by default; rights confirmed before publishing | Terms of use, takedown process |
| Living people | Hidden by default; flagged before publishing | UK GDPR, DPIA, controller/processor roles |
| Sensitive data | Extra care for health, beliefs, criminal records, children | Lawful basis, retention |
| AI use of content | Separate permissions for processing someone's archive and for improving the product | Consent wording, model training |
| Contributor collections | Contributors keep ownership; written terms for hosting, indexing, AI use, redistribution and exit | Contributor agreement |
| Old photos and film | Owning an item doesn't mean owning its copyright | Copyright, orphan works |
| Open data | Every record keeps its dataset's licence; ODbL and CC BY-SA may require share-alike | Effect on combined data |
| Software | Every dependency and licence recorded; GPL/AGPL kept out of the core | AGPL/GPL obligations |
| Payments | No third-party funds held directly | Payment regulation, tax |
| Tips | "Tip"/"support" wording | Charity law, Gift Aid |
| Forums | Reporting, moderation, block lists, rules | Online safety duties |
| Recordings | Tell everyone being recorded; record consent | Consent with vulnerable relatives |

A single record can carry several independent rights: the underlying work, the photograph, the scan, the transcription, the database, personal data, metadata and the API contract. Public-domain originals don't make every reproduction free.

**Misuse to guard against:** doxxing or stalking living people, identity fraud, defamatory false identification, fake oral histories, copyright infringement, scraping abuse. Constrain bulk export, audit external access, run a takedown and appeal process.

**Other rules:** full export, account deletion and a plan for service closure; log who changed each claim, permission and publication; keep contributor agreements attached to their collections; show every image's rights status before publishing; never copy from websites or APIs beyond their terms.

## 12. Build plan

Vertical slices, starting with a working Research assistant and the Cheap Street demo. Don't start the next package until its gate is met. Timings are rough for a small team; revise after WP2.

### WP1 — Foundation (≈1–2 weeks)
- Repo, Docker Compose (Postgres + PostGIS + pgvector, Redis), Django, React app, env files, Sentry hook.
- Linting, formatting, tests and CI before feature work.
- Accounts (allauth), profiles, projects, chats, messages, basic permissions.
- Interface shell ported from the prototype: layout, design tokens, new-chat prompts, routing for every top-level view (placeholders where the feature is later).
- Streaming chat via the Anthropic API behind the provider adapter; messages saved.
- **Done when:** a user can sign in, create a project and hold a saved, streamed chat.

### WP2 — Research core and source directory (≈2–3 weeks)
- History tables: sources, source records, places, addresses, events, assertions, evidence, decisions; date-precision and geocode-precision fields.
- Source directory seeded from `DATA_SOURCES.md`, with directory fields, data status labels and acceptance scores.
- Assistant tools with citations and a "What I checked" block.
- Hand-checked Cheap Street dataset using only material we may store.
- Evaluation set: questions with known answers and citations, plus no-result cases.
- **Done when:** the Pigeons question returns sources, the address conflict and next steps, with no invented facts.

### WP3 — Evidence panel and Archive Explorer (≈3–4 weeks)
- Shared connector interface and a contract test harness (search, get_record, pagination, rate-limit, provider-down, access-denied).
- Hosted GB1900 connector; Wikidata connector once terms are confirmed; National Archives Discovery once access is approved; Europeana once its key and terms are confirmed.
- Explorer: virtualised table, cursor paging, filters, record detail, next/previous, Research Basket, record-to-chat bridge.
- Evidence comparison and project decisions.
- **Done when:** a user can browse a source, save a record and ask the assistant about it.

### WP4 — Record (≈4–6 weeks)
- Archive uploads, folders, previews, ingestion pipeline with scanning, processing jobs.
- PDF and OCR extraction; handwriting as a credit-based job.
- GEDCOM import/export and tree view; family pages built from assertions.
- **Done when:** a real GEDCOM and a folder of family documents can be imported and corrected.

### WP5 — Live guided interview (≈3–4 weeks)
- Speech comparison spike (accuracy, delay, cost; British accents; older speakers).
- Streaming audio, live text and the sentence animation.
- Background extraction and non-intrusive prompts.
- Audio, transcript, end-of-session response, links back to source lines.
- **Done when:** five real interviews are completed and people want to continue.

### WP6 — Time map and Search (≈3–4 weeks)
- MapLibre, map layers cleared for use, year slider.
- Dated records, photos, memories and events on the map.
- Search across permitted content and service listings.
- **Done when:** someone can explore Cheap Street through time with public and private items clearly separated.

### WP7 — Home and migration (≈4–6 weeks)
- Server-rendered homepages, posts, collections, approval flow, pre-publish check.
- WordPress import with redirects; prepared social posts, then direct posting one platform at a time.
- **Done when:** three historians have moved or published work and still have a full export route.

### WP8 — Connect and payments (≈3–5 weeks)
- Directory, profiles, listings, coverage areas, enquiries.
- Forums with moderation tools.
- Credits, tips, the ledger, contributor panel and statements (contributor phases 1–2).
- **Done when:** people can find a local specialist and tip or contact them.

### Testing

- **Fake data** in development and tests, labelled `prototype_fixture`.
- **Evidence accuracy:** question sets with known answers and citations.
- **No-result cases:** the assistant admits when it can't find something.
- **Rights:** private files never appear in another person's search, thumbnails, embeddings, citations or answers.
- **Provenance:** every Explorer row has a provider ID, record ID and original link or internal path.
- **Pagination:** sorting and filtering stay stable across hundreds of pages.
- **Evidence:** conflicting assertions persist and are never auto-merged.
- **Charges:** nothing is charged for scrolling, repeated searches or ineligible citations.
- **Network:** unavailable APIs show a disabled state, not invented answers.
- **Export:** users can download originals and metadata, subject to third-party rights.
- **Publication:** requires preview and an explicit affirmative action.
- **User tests** include older users and family historians early.

## 13. Open decisions

- Is the £20 a one-off credit purchase, a monthly plan or both?
- Is ArchiveHub the final name?
- Under Discern-AI or a separate company?
- Which code from Mint and Folio can be reused? (Mint is React + TS + Vite; its components may carry over to `apps/web`.)
- Speech on our own servers or a hosted API? (Decided by the WP5 spike.)
- Storage limits and retention promise per plan, including after a subscription lapses.
- The percentage of revenue going to the contributor pool.
- Which 3–5 Berkshire historians and organisations to approach first.
- Which rights can be secured for the Cheap Street demo.
- Who moderates forums and handles takedowns, and who has editorial authority over disputed community archives.
- How multiple contributors correct a shared historic person, place or entity.
- Which histories are publicly indexed versus visible only to collaborators.
- Baseline cost of processing a 100-page manuscript or an hour of video.
