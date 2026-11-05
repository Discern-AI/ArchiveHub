# WP2 — Research core and source directory

**Gate (SPEC §12):** the Pigeons question returns sources, the conflict and next steps, with no invented facts.

**Status (5 Nov 2026):** built and tested offline. The gate itself is measured by `run_evals`, which needs API credit and has not been run yet.

## What was built

- **History tables** (`services/api/history`): Source (also the directory entry), SourceRecord, Place, Address, Organisation, Person, Event, Assertion, AssertionEvidence, Decision. Dates keep the original wording plus searchable years and a precision. Places use latitude/longitude until WP6 (ADR-019).
- **Source directory:** 36 entries seeded from `DATA_SOURCES.md` (`history/data/sources.json`), with access type, cost, licence, conditions, storage policy, data status label, tier and review status.
- **Checked Cheap Street dataset** (`history/data/cheap_street.json`): 9 records, 6 pubs, 22 claims, 29 evidence links. Every fact was checked against its live page on 5 Nov 2026 and is stored in our own words with a link (ADR-018). Historic England's photo record was left out because its page blocked checking.
- **Assistant tools:** `search_source_directory`, `search_records`, `get_record`, `compare_claims`. Every input is validated; results respect project privacy; living people are never surfaced.
- **Citations and "What I checked"** are built by the server from the tool calls (ADR-020). A citation number no tool returned is never shown; the model can't add links.
- **Clear errors:** API key, billing, busy and unreachable problems each get their own message.
- **Evaluation set** (`assistant/evals/questions.json`, 6 questions) with deterministic grading, including the gate question, a "when did it close?" trap (no closure date exists) and an unknown pub.

## Findings while checking sources

- The prototype said the Catherine Wheel was recorded from 1864. Pub Wiki's earliest entry is **1796** (John Salter, Berkshire Directory). The dataset uses 1796.
- Pub Wiki's Pigeons list runs to **1940**; the 1970 listing comes from its separate Kelly's 1970 page.
- Closed Pubs gives **69 Cheap Street** with no source; Pub Wiki, Kelly's 1970 and the 1911 census summary give **5 Cheap Street**. The 1871 census note gives **9 St Marys Hill**.
- Pub Wiki pages state "All rights reserved", so its material stays reference-only until permission is agreed.

## Running it

```bash
cd services/api
python manage.py migrate
python manage.py load_reference_data   # safe to rerun
python manage.py run_evals --live      # uses API credit; add --report evals.json to save answers
```

## Known limits

- Search is simple word matching over a small dataset; Postgres full-text and vector search come when there's more data.
- The evidence panel and Archive Explorer (where people browse records and record project decisions) are WP3. `Decision` exists in the data model but has no screen yet.
