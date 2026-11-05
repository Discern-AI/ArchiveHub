# WP3 — Evidence panel and Archive Explorer

**Gate (SPEC §12):** a user can browse a source, save a record and ask the assistant about it.

**Status (5 Nov 2026):** built and tested. Browsing, saving and sending a record to the assistant work end to end in tests; the assistant's actual answer needs API credit, as in WP2.

## What was built

- **Connector framework** (`services/api/connectors`): one interface for every source (`search`, `get_record`, `citation`, `storage_policy`), normalised records, cursor paging, and one set of errors (unavailable, rate limited, access denied, not found, bad query).
- **Contract test harness:** the same tests run against every connector: search, record detail, paging with no repeats, unknown records, bad cursors, and how live failures (429, 403, 5xx, timeouts) are reported.
- **Three connectors:**
  - *ArchiveHub checked records*: the WP2 Cheap Street facts.
  - *Old map names (OS six-inch, c.1900)*: hosted, from the GB1900 raw dump (CC0). 15,188 labels for Newbury and West Berkshire (ADR-021).
  - *Wikidata*: live search, CC0 confirmed, descriptive User-Agent, checked against the real service.
- **Not built, as the spec requires:** National Archives Discovery (waits for API access approval; its terms forbid caching) and Europeana (waits for key type and terms).
- **Archive Explorer** (right-hand workspace): pick a source, search or browse, page through results, open a record, step to the previous/next record, open the original, see how to cite it and its rights.
- **Research Basket:** save a record to a project. A copy is kept only where the source allows it; otherwise just the link and our notes.
- **Ask about this record:** the selected record goes to the assistant as clearly marked data (never as instructions), numbered so the answer can cite it.
- **Evidence panel:** when sources disagree, the answer shows "Sources disagree … Compare sources". The panel shows each answer simply, with the full comparison (what each source says, suggested weight and who suggested it) one click away. A project can use one answer or keep it disputed, with a reason. "Use" doesn't mean "true", and nothing is deleted.
- **Assistant:** a new `search_connector` tool for the old map names and Wikidata.

## Findings

- The c.1900 six-inch map marks "CHEAP STREET" where expected (51.4005, −1.3231), but doesn't name individual town-centre pubs; larger-scale town plans would be needed for that (NLS maps, a WP6 check).
- wikidata.org failed certificate checks in Python but not in Windows: fixed by verifying with the OS trust store (ADR-022).

## Running it

```bash
cd services/api
python manage.py load_reference_data
# Download the GB1900 raw dump (≈311 MB) from https://www.visionofbritain.org.uk/data/ into var/downloads/gb1900/
python manage.py import_old_map_names --zip var/downloads/gb1900/GB1900_final_raw_dump_july_2018.zip
```

The import reads about 10.7 million rows straight from the zip and takes a few minutes. Downloaded files live under `services/api/var/`, which is never committed.

## Known limits

- The Explorer pages 25 records at a time rather than scrolling continuously (ADR-023).
- Map views and "Surprise me" come with the time map (WP6).
- Decisions are recorded but not yet used elsewhere (e.g. in family pages or drafts).
