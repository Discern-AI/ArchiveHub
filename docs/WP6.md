# WP6 — Time map and Search

**Gate (SPEC §12):** someone can explore Cheap Street through time with public and private items clearly separated.

**Status (6 Nov 2026):** built and tested, including a run in a real browser (Chrome) against the real servers: the map draws, pins and the year slider work, a memory can be added by clicking the map, today's map shows alongside, and Search finds the new memory. **Still to do for the gate:** set up a MapTiler key so the historic OS maps appear, then have a few people (including an older user) explore Cheap Street and say whether the public/private split is clear.

## What was built

- **Time map** (`/map`, top bar → Map), starting at Cheap Street:
  - **Year slider** (1700 to today) with "years either side" (±5, ±10, ±25 or any date). The year is kept in the link (`/map?year=1911`).
  - **Old map matching the year:** the most detailed NLS historic OS map covering that year (six-inch 1888–1913, 1920s–1940s, 1:25,000 1937–1961), with a strength slider. You can also pick one or turn them off. Without a MapTiler key the layers are listed as "not available", the page says so, and you see today's map instead (ADR-031).
  - **Today alongside:** a second map of today, moving with the first.
  - **Old map names** (c.1888–1913, CC0) as brown labels when you're zoomed in to about a town centre and the years cover c.1900.
  - **Public and private kept apart (ADR-032):** public records are round green pins and a "Public records" list; your projects' items are square purple "P" pins and a "Private: your projects" list in a purple box that says who can see them. Items at the same spot share one pin with a count; clicking it lists just those items.
  - **Every date says what kind it is:** *Happened*, *Made or taken*, *Record covers* (e.g. a licensee list 1851–1940) or *Map surveyed*. Undated items appear only with "Include undated".
  - **Location precision is shown,** e.g. "Street-level location" for records placed at Cheap Street's point. Nothing is placed more precisely than its source allows. St Marys Hill isn't on the c.1900 map names, so it isn't placed.
  - **Add a memory or photo:** pick a project, click the map (or use the middle of the map), say whether the date is when it happened or when the photo was taken, how sure the location is, and add it. Photos and documents come from the project's Archive. Interview passages can be placed through the API (`kind: "interview"` with transcript lines); a button on the interview page can come later. Items can be removed from the map with a confirmation, which doesn't touch the file or interview.
- **Search** (`/search`, top bar → Search): places, pubs and businesses, checked records, names on the c.1900 map and the source directory (public), plus your map items, Archive files (names and text read from them), interview transcript lines and family-tree people (private, marked "Private"). Each group says exactly what it looked at. A **"What was searched / Not searched"** block lists forums and the services directory (not open until WP8), live sources (searched one at a time in the Explorer) and link-out sources. An empty result says plainly that it isn't proof of absence (ADR-033).
- **Server:** `services/api/timemap` (map items, area/year queries, layers) and `services/api/search`. Places now carry where their coordinates come from (`Place.geocode_source`); Newbury, Cheap Street and Greenham Road are placed from the old map names. Locations stay as latitude/longitude (ADR-030, superseding ADR-019's PostGIS plan).

## Privacy checks (tests)

- Another person never sees your map items, project claims, files, transcript lines or family-tree people in the map or in Search, and can't change or delete your items.
- Project viewers see the project's map items but can't add them.
- Claims about people are not mapped, so living people can't be located through the map.
- A photo must be an image from the same project; interview passages must cite lines that exist.
- Search and the map never charge credits.

## Running it

Nothing new is needed for today's map (OpenFreeMap, no key). For historic maps:

1. Create a free MapTiler account and an API key. **Restrict the key to your own sites** in MapTiler (keys are visible in the browser by design).
2. Set `MAPTILER_KEY=...` in `services/api/.env` and restart the API.

MapTiler's free plan is for non-commercial use up to 100,000 tiles a month; **a paid plan is needed before launch** (ADR-031). The National Library of Scotland's maps are CC BY 3.0; the attribution is shown on the map whenever a historic layer is on.

Old map names on the map need the GB1900 import from WP3 (`import_old_map_names`).

## Known limits

- **Not yet seen with a real MapTiler key:** the layer settings follow MapTiler's TileJSON format, but the historic tiles haven't been viewed on screen.
- **Few public items so far:** 9 checked records and 22 claims, most placed at street level, so most public pins share one spot on Cheap Street. Individual buildings need address-level locations, which the c.1900 six-inch map doesn't give for town-centre pubs (WP3 finding). Larger-scale town plans would help.
- **Search matches words, it doesn't rank them.** Every word must appear; there's no stemming ("pub" doesn't find "pubs") or spelling tolerance. Postgres full-text and vector search come with larger datasets (ADR-033).
- **Family-tree places aren't on the map:** GEDCOM places are text, not locations. Geocoding them (with a precision and source) is a later step.
- **Map pins need a mouse or touch to place;** keyboard users can place an item at the middle of the map and move the map with the arrow keys first.
- **Two maps side by side** follow each other but aren't a swipe comparison; that can come if people ask for it.
- Postgres was not available locally; CI runs the tests on Postgres.
