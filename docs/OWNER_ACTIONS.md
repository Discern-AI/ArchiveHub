# Owner actions

Everything waiting on the owner: accounts, keys and applications to send, partners to contact, things built that still need a real-world check, and decisions. Ready-to-send wording is in [OUTREACH.md](OUTREACH.md); details of every source are in [SOURCE_REGISTER.md](SOURCE_REGISTER.md). Tick items off here as they're done.

Keys go in `services/api/.env` (never committed). Restart the API afterwards, then run:

```bash
cd services/api
python manage.py check_connectors        # one live search per source: works / not set up / failed
```

Last updated: 7 Nov 2026.

---

## 1. Do first

| # | Action | Why it matters | Where | Cost | Then |
|---|---|---|---|---|---|
| 1 | ~~Add credit to the Anthropic API account~~ **Done 10 Nov 2026**: evaluation 6/6, interview notes, responses and handwriting all work for real | The assistant's real answers, the WP2 evaluation, handwriting reading and interview notes have never run against the real API (the account has no credit). Everything else is tested; these aren't | console.anthropic.com → Billing | Pay as you go | Run `python manage.py run_evals` (WP2 gate) and try a chat |
| 2 | **Email The National Archives** for Discovery API access | Unlocks the Royal Berkshire Archives' catalogue and ~2,500 others | Draft: OUTREACH.md §1 (add the server's IP address) | Free | `TNA_DISCOVERY_ENABLED=true` |
| 3 | **Create a MapTiler account and key** | Historic OS maps on the time map (needed for the WP6 gate) | maptiler.com (free plan for the pilot) | Free now; paid plan before launch | `MAPTILER_KEY`; restrict the key to our domains in MapTiler |
| 4 | **Email the National Library of Scotland** | Confirms commercial use of their historic maps, which the time map depends on | Draft: OUTREACH.md §2 | Free | Record the answer in the register |
| 5 | **Get the free keys** (about 30 minutes in total) | Each adds a source to Search, the Explorer and the assistant | Table in §2 below | Free | `check_connectors` |

## 2. Accounts and API keys

| Service | What it adds | Where to sign up | Setting | Cost and terms | Status |
|---|---|---|---|---|---|
| Anthropic API | The assistant, handwriting, interview notes | console.anthropic.com | `ANTHROPIC_API_KEY` (set) | Pay as you go | **Done** (credit added 10 Nov 2026) |
| MapTiler | NLS historic OS maps | maptiler.com | `MAPTILER_KEY` | Free plan non-commercial; paid before launch | To do |
| OpenAlex | Academic research (works now on a small shared budget) | openalex.org/settings/api | `OPENALEX_API_KEY` | Free | To do |
| GeoNames | Place names worldwide | geonames.org (create account, switch on free web services) | `GEONAMES_USERNAME` | Free; CC BY | To do |
| Geograph | Located photos of Britain | geograph.org.uk → Help → API | `GEOGRAPH_API_KEY` | Free; credit photographers | To do |
| OS Data Hub | Today's places and streets (OS Names) | osdatahub.os.uk (create a project, add OS Names) | `OS_DATA_HUB_KEY` | Free; OGL | To do |
| Europeana | 50m+ European items | pro.europeana.eu: request a **project** key (OUTREACH.md §3) | `EUROPEANA_API_KEY` | Free | To do |
| DigitalNZ | NZ newspapers (Papers Past) | digitalnz.org → My API key | `DIGITALNZ_API_KEY` | Free; commercial terms | To do |
| DPLA | US collections | dp.la API page (key by email). **Read their API terms first**: we couldn't | `DPLA_API_KEY` | Free | To do |
| Trove | Australian newspapers | trove.nla.gov.au: apply for the **commercial** level (OUTREACH.md §7) | `TROVE_API_KEY` | Free key; commercial use needs NLA permission; renews yearly | To do |
| Sentry (optional) | Error alerts | sentry.io | `SENTRY_DSN` | Free tier | Optional |
| Wolfram\|Alpha (optional) | Calculations | products.wolframalpha.com/api | not built | Commercial licence needed | Later |

After adding keys, four connectors still need their first live run: **Trove, DPLA, OS Names and GeoNames** (built from their documentation). `check_connectors` does it.

## 3. Applications and permission requests

| To | What for | Draft | Status |
|---|---|---|---|
| The National Archives | Discovery API access | OUTREACH.md §1 | Not sent |
| National Library of Scotland | Commercial use of historic maps; Data Foundry | OUTREACH.md §2 | Not sent |
| National Library of Australia | Trove commercial use | OUTREACH.md §7 | Not sent |
| Open Library | Commercial use of the API (or use dumps) | OUTREACH.md §8 | Not sent |
| UK PlanIt | Planning applications near a building | OUTREACH.md §8 | Not sent |
| Library of Congress | Their API blocked our server with a bot challenge | Short email asking for API access | Not sent |
| World Historical Gazetteer | Commercial use (default licence is non-commercial) | Short email | Not sent |
| Portable Antiquities Scheme, Open Domesday | Their licences aren't stated | Short emails | Not sent |
| V&A | Read section 9.3 of their website terms (we couldn't) | Reading task | To do |
| HM Land Registry / Royal Mail | Whether Price Paid addresses can be shown in a property history feature | Legal question | Later |
| FamilySearch | Innovator Program (closed API; long process) | Application | Later |
| Mass Observation (The Keep), Great Diary Project, UK Data Service | Access to testimony collections | Later | Later |
| Free UK Genealogy | Bulk access to FreeBMD, FreeREG, FreeCEN indexes (their research data programme) | OUTREACH.md §9 | Not sent |
| UK Data Service | I-CeM census microdata (statistics now; ask about named records) | OUTREACH.md §10 | Not sent |
| Jisc Archives Hub | Reuse terms for catalogue descriptions via their SRU/OAI-PMH interfaces | Short email | Not sent |
| CAMPOP (Cambridge) | Historical occupation datasets for context | Short email | Not sent |
| Cambridge Alumni Database | Reuse of the experimental alumni database | Short email | Not sent |

## 4. Partners to contact

Drafts for the first two are in OUTREACH.md §5–6. Full list: SOURCE_REGISTER.md §8.

| Organisation | Why | Status |
|---|---|---|
| Royal Berkshire Archives (Berkshire Record Office) | Licensing records, deeds, sale particulars; **launch partner** | Not contacted |
| West Berkshire Museum | Objects and photos; **launch partner** | Not contacted |
| Newbury Weekly News | Newspaper archive | Not contacted |
| Pub Wiki, Closed Pubs, Nickbits | Pub histories; invite as contributors, ask about reuse | Not contacted |
| Berkshire Family History Society | Indexes and members | Not contacted |
| West Berkshire Historic Environment Record | Archaeology and buildings | Not contacted |
| Newbury and Reading local studies libraries | Directories, maps, photos | Not contacted |
| Museum of English Rural Life (Reading) | Rural life, Berkshire | Not contacted |
| Local history societies (e.g. Newbury District Field Club) | Early historians for WP7 | Not contacted |
| Free UK Genealogy | FreeBMD, FreeCEN, FreeREG | Not contacted |
| Wessex Film and Sound Archive | Regional film | Not contacted |
| University of Leicester | Historical trade directories | Not contacted |

## 5. Built, but needs a real-world check

| Area | What's needed | Gate |
|---|---|---|
| Assistant (WP2–3) | **Done:** `run_evals --live` 6/6 on 10 Nov 2026. Try your own questions in the app | WP2: the Pigeons question answered with sources, the conflict and next steps |
| Record (WP4) | Import a real GEDCOM and a folder of family documents (with family consent), then correct them | WP4 |
| Handwriting reading | Works on a synthetic letter; try one real old letter | — |
| Interviews (WP5) | **Five real interviews** with older relatives or volunteers, with consent | WP5 |
| Speech spike | ~10 consented 2–5 minute recordings (half from speakers over 70, local accents) with careful transcripts, then `python manage.py speech_spike` | Confirms ADR-028 |
| Interviews on phones | Try an interview on an iPhone (Safari) and an Android phone | — |
| Time map (WP6) | MapTiler key, then check the historic layers on screen; then 2–3 people (one older) explore Cheap Street and say whether public and private are clearly apart | WP6 |
| Connectors | Run `check_connectors` after adding keys (Trove, DPLA, OS Names, GeoNames untested) | — |

## 6. Before any public launch

| Item | Why | Ref |
|---|---|---|
| Install a malware scanner (e.g. ClamAV) for uploads | Uploads aren't scanned yet | ADR-026 |
| Paid MapTiler plan | Free plan is non-commercial | ADR-031 |
| OpenAlex key for production | Keyless use shares a small daily budget | ADR-036 |
| Ask TNA whether assistant answers written from Discovery results may be kept in chat history | Their terms forbid storing API content | ADR-034 |
| Privacy notice listing who receives data: Anthropic (chats, files sent to the assistant), the map tile services (IP addresses), outside sources (search words, only when the user ticks "outside sources") | Required, and fair | SPEC §11 |
| Legal or specialist review of the rights checklist | SPEC says so | SPEC §11 |
| Credits actually charged, with a ledger | Estimated and recorded only | ADR-027, WP8 |
| Production settings: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, allowed hosts, HTTPS, R2 storage, Sentry | Development defaults now | ADR-012 |
| Hosting: Postgres 16 + PostGIS + pgvector, Valkey, a server for speech (GPU later) | Runs on a laptop now | ADR-004, ADR-028 |
| Check the FFmpeg build bundled with PyAV (speech spike only) | LGPL obligations | DEPENDENCIES.md |
| Takedown and appeal process; named moderation owner | Misuse rules | SPEC §11 |

## 7. Housekeeping

- **Restart your dev servers** on ports 8000 and 5173: they're running code from before WP6. Database changes are already applied to `db.sqlite3`.
- Optional installs: Tesseract (printed-text OCR), `pip install -r requirements-speech.txt` (speech models, ~600 MB).
- New machines need the old map names import (download ~311 MB; see docs/WP3.md). The whole of Great Britain takes about 28 minutes.
- **Northern Ireland listed buildings** are a monthly download, not a live service. Each month (or before launch), download the GeoJSON from Open Data NI ("Listed Buildings Northern Ireland") and run `python manage.py import_ni_listed_buildings --file <path>`. Until it's run, the map says Northern Ireland's list hasn't been loaded.
- ESLint's development-only advisories (minimatch) wait for a typescript-eslint update.

## 8. Decisions waiting on you

**Product (raised in this phase):**
- A "Context and connections" work package before WP7: explaining records (jobs, Poor Law, money), "What was here in 1905?", research trails including the wider family search, and person matching that a person always decides.
- An opt-in public memory bank from ArchiveHub's own interviews (separate consent, withdrawable).
- A "Property and neighbourhood explorer" (planning, sales, listed buildings, old maps), once Land Registry and PlanIt terms are clear.

**From SPEC §13:**
- £20: one-off credits, monthly plan or both?
- Final name; Discern-AI or a separate company?
- Storage limits and retention per plan, including after a subscription lapses.
- Contributor pool percentage.
- First 3–5 Berkshire historians and organisations.
- Rights for the Cheap Street demo.
- Who moderates forums and handles takedowns; editorial authority over disputed community archives.
- How several contributors correct a shared historic person or place.
- What's publicly indexed versus visible only to collaborators.
- Baseline cost of a 100-page manuscript or an hour of video.
