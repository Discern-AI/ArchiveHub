# Live connectors: keys and setup

Each connector stays switched off, and is listed in the Explorer as "not available here yet", until its key is set in `services/api/.env` (ADR-034). Restart the API after adding a key. Never commit keys.

| Source | Setting | How to get access | Terms to know | Tested against the real service |
|---|---|---|---|---|
| Europeana | `EUROPEANA_API_KEY` | Request a **project** key at pro.europeana.eu (personal keys are for individual, non-production use) | Metadata CC0, commercial use allowed. Media rights per item. Keys can't be shared | Yes (demo key) |
| The National Archives: Discovery | `TNA_DISCOVERY_ENABLED=true` | Email webmaster@nationalarchives.gov.uk with the server's IP address, the site's link and how it's used | **Nothing returned may be cached or stored.** At most 3,000 calls a day, one a second. Beta service, no guarantee | Yes |
| Geograph | `GEOGRAPH_API_KEY` | Request a key on geograph.org.uk (Help → API) | Photos CC BY-SA 2.0: credit the photographer, say it's Creative Commons, link the photo. No bulk collection or model training via the live API | Yes |
| OS Names | `OS_DATA_HUB_KEY` | Create a project in the OS Data Hub (free plan) and add the OS Names API | Open Government Licence. Show "Contains OS data © Crown copyright and database right" | No (documented format) |
| DigitalNZ (incl. Papers Past) | `DIGITALNZ_API_KEY` | Create an account at digitalnz.org, then "My API key" | Commercial use only with a key and only for selected metadata. Name the original source and link via `source_url`. 10,000 calls a day | Yes |
| Trove (Australia) | `TROVE_API_KEY` | Apply on trove.nla.gov.au. **Commercial use needs the NLA's explicit permission** (commercial access level) | Acknowledge Trove and the NLA. Keys expire after 12 months | No (documented format) |
| DPLA (USA) | `DPLA_API_KEY` | Request a key through the DPLA API (it's emailed to you) | Metadata CC0. Item rights vary. Their API terms page couldn't be read automatically: confirm before launch | No (documented format) |

Not built: **FamilySearch.** Its API is closed to the public; production access needs an approved Innovator Program application, a compatibility review and signed agreements.

Already working without keys: Wikidata, old map names (c.1900), ArchiveHub's checked records.

## What each adds

- **Europeana:** maps, photos and documents from European institutions (e.g. a 1768 "Map of the Country ten miles round Newbury").
- **TNA Discovery:** catalogue entries for about 2,500 UK archives, including the Royal Berkshire Archives (e.g. "Sale particulars of 62 Cheap Street, Newbury", 1933). It tells you a document exists and where; you visit or order a copy to see it.
- **Geograph:** photos of the same streets in recent decades, with photographer, date and location.
- **OS Names:** where a place or street is today, for placing addresses on the map.
- **DigitalNZ, Trove, DPLA:** newspapers and collections abroad, for relatives who emigrated.

## Where they appear

- **Archive Explorer:** pick the source, search, open a record, save it to a project.
- **Assistant:** the `search_connector` tool can use any of them, with numbered citations the server builds.
- **Search page:** lists them under "Not searched" (searched one source at a time for now).
