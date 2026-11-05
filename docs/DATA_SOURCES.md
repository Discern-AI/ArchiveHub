# Data sources

Merged from the Spec and the Blueprint. **Every access and licence entry is provisional** until its terms are re-read and, where needed, legally confirmed. A URL existing is never evidence of a live connector.

- **Status** — "Page read": terms/access page was read for the Spec (5 Nov 2026), still needs legal confirmation. "Partly checked", "Not yet checked" as stated.
- **Tier** (Blueprint) — `A` investigate for an initial live connector · `B` linked/federated discovery · `C` licence or partnership required · `D` reference dataset, no broad programmatic rights assumed.
- **Plan** — what ArchiveHub does with it now.

Every directory entry in the product holds: subject, area, dates, record types, holder, website, access type, cost, API status, licence, commercial reuse, AI reuse, storage rules, attribution wording, contact, last checked, owner of the next action, data status label and acceptance score.

**Acceptance scorecard (0–5 each):** research value, temporal/geographic coverage, unique records, quality, legal reuse clarity, API stability, browsing support, full-text/media availability, cost, contributor relationship, maintenance effort. Store score and rationale.

**In the product:** these entries are seeded into the source directory from `services/api/history/data/sources.json` (keep the two in step). Checked Cheap Street facts are in `history/data/cheap_street.json`; see [WP2.md](WP2.md) for what was checked and what changed.

## Launch candidates

| Source | Offers | Access | Conditions found | Status | Tier | Plan |
|---|---|---|---|---|---|---|
| [GB1900 Gazetteer](https://www.visionofbritain.org.uk/data/) | Place names from old OS maps | Download | Raw Dump CC0; Complete/Abridged CC BY-SA, commercial use allowed | Page read | A | **First hosted dataset**, map search (WP3) |
| [Wikidata](https://www.wikidata.org/) | People, places, organisations | API / SPARQL / dumps | Confirm current terms | Not yet checked | A | Entity matching and context; never genealogical proof |
| [National Archives Discovery](https://discovery.nationalarchives.gov.uk/) | 32–37m catalogue descriptions (metadata, not document text) | API, access requested by email | One page cites OGL; [API terms](https://www.nationalarchives.gov.uk/terms-and-conditions/discovery-for-developers-about-the-application-programming-interface-api/) say don't cache or store | Page read | A | Live search only until clarified; contact TNA |
| [Europeana](https://www.europeana.eu/) | European cultural objects | [API](https://api.europeana.eu/en), personal vs project keys | Per-item rights | API docs referenced | A | Connector once key type, limits and attribution confirmed |
| [OpenHistoricalMap](https://www.openhistoricalmap.org/) | Time-aware map data | Data and tools | Confirm licence and Newbury coverage | Not yet checked | A | Test for the time map |
| [FamilySearch API](https://www.familysearch.org/developers/) | Family Tree and related data | Developer programme | Licensing terms; partners need a business plan and roadmap | Page read | B/C | Apply early; optional |
| [Vision of Britain / GBHDB](https://www.visionofbritain.org.uk/) | Historical statistics and boundaries | UK Data Service | Statistics open; boundaries limit commercial use; parish boundaries commercially licensed | Page read | B/D | Later context layer |

## UK genealogy and civil records

| Source | Records | Conditions found | Status | Tier | Plan |
|---|---|---|---|---|---|
| [Free UK Genealogy](https://www.freeukgenealogy.org.uk/) (FreeBMD, FreeCEN, FreeREG) | BMD indexes, census and parish transcriptions | ODbL, but sharing hasn't started; commercial use not addressed; old FreeBMD FAQ mentions an ONS free-access condition | Page read | A/B | Link out, then contact them |
| [I-CeM](https://www.essex.ac.uk/research-projects/integrated-census-microdata) | ~230m census person records, 1851–1921 | Names/addresses need a special licence; commercial use not addressed | Page read | C/D | Research use only until cleared |
| [General Register Office](https://www.gro.gov.uk/gro/content/certificates/) | Official BMD records | Confirm reuse terms | Not yet checked | B/C | Link out and explain |
| [Findmypast](https://www.findmypast.co.uk/) | Census, parish, military, newspapers, 1921 census | Licensing conversation needed | Partly checked | C | Link out; explore partnership |
| [Ancestry](https://www.ancestry.co.uk/) | Census, parish, military, trees | Confirm terms | Not yet checked | C | Directory only; GEDCOM import from user exports |
| [FamilySearch records](https://www.familysearch.org/) | Global indexes and images | Access varies by collection | Partly checked | B/C | Link out, or API if approved |
| [ScotlandsPeople](https://www.scotlandspeople.gov.uk/) | Scottish BMD, census | Pay-per-record | Not yet checked | C | Link out |
| [National Archives of Ireland](https://www.nationalarchives.ie/) | 1901/1911 census and more | Reuse per resource | Not yet checked | B | Link and assess |
| [IrishGenealogy.ie](https://www.irishgenealogy.ie/) | Irish civil and church records | — | Not yet checked | B/C | Link and assess |

TNA notes the 1921 census is free to view only at specified physical locations; full digitised censuses 1841–1921 are via commercial partners.

## Archives, catalogues and aggregators

| Source | Data | Tier | Plan |
|---|---|---|---|
| [Wikimedia Commons](https://commons.wikimedia.org/) | Openly licensed media, per-file licences | A/B | Photo connector showing each file's licence |
| [Archives Hub](https://archiveshub.jisc.ac.uk/) | UK archival descriptions | B | Evaluate interfaces |
| [Archives Portal Europe](https://www.archivesportaleurope.net/) | European archive descriptions | B | Later |
| [Internet Archive](https://archive.org/) | Books, film, audio | B | Connector respecting item-level rights |
| [British Library](https://www.bl.uk/) | Manuscripts, books, sound, news | B/C | Collection-specific |
| [US National Archives](https://www.archives.gov/research/catalog), [DPLA](https://dp.la/), [Smithsonian Open Access](https://www.si.edu/openaccess), [Rijksmuseum](https://data.rijksmuseum.nl/) | Overseas catalogues and objects | B | Later expansion |

## Newspapers, books and text

| Source | Content | Status / caveat | Plan |
|---|---|---|---|
| [British Newspaper Archive](https://www.britishnewspaperarchive.co.uk/) | British and Irish newspapers | Run by Findmypast, a potential competitor; no bulk access | Link out, ask about licensing |
| [BL news datasets](https://bl.iro.bl.uk/) | Newspaper metadata; some open OCR research datasets | Check each item's licence | Evaluate |
| [LwMDB](https://www.lancaster.ac.uk/) | Metadata on 19th-century newspapers | Code MIT; confirm data licence. Page read | Newspaper discovery by place and title |
| Newbury Weekly News archive | Local coverage | Contact publisher; not yet checked | Valuable local partnership |
| [British History Online](https://www.british-history.ac.uk/) | Primary/secondary texts | Free and premium sections differ | Directory, assess |
| [Old Bailey Online](https://www.oldbaileyonline.org/) | London trials 1674–1913 | Verify terms/format | Later specialist connector |
| [Historic Hansard](https://api.parliament.uk/historic-hansard/), [UK Parliament data](https://developer.parliament.uk/) | Debates and metadata | Verify coverage | Later |
| [Project Gutenberg](https://www.gutenberg.org/), [HathiTrust](https://www.hathitrust.org/), [Google Books](https://books.google.com/), [Oxford Text Archive](https://ota.bodleian.ox.ac.uk/) | Books and texts | Rights vary by item and territory | Directory |
| [Welsh Newspapers Online](https://newspapers.library.wales/) | Welsh newspapers | Evaluate rights | Directory |

## Military, legal and special collections

| Source | Records | Status | Plan |
|---|---|---|---|
| [Commonwealth War Graves Commission](https://www.cwgc.org/) | War dead and cemeteries | Not yet checked | Directory, then check data access |
| [Lives of the First World War](https://livesofthefirstworldwar.iwm.org.uk/) | FWW life stories | Not yet checked | Directory, possible links |
| [Imperial War Museums](https://www.iwm.org.uk/collections) | Photos, oral testimony, AV | Not yet checked | Catalogue and permissions |
| [A Street Near You](https://astreetnearyou.org/) | FWW records mapped to places | Site found, terms not checked | Design reference, possible partner |
| [BFI](https://www.bfi.org.uk/) / [BFI Player](https://player.bfi.org.uk/) | Film archive | Not yet checked | Outbound links only |

## Maps, photos, buildings and local sources

| Source | Offers | Status | Plan |
|---|---|---|---|
| [National Library of Scotland maps](https://maps.nls.uk/) | Historic OS maps | Terms not checked | **Priority check** for time-map layers |
| [Historic England archive](https://historicengland.org.uk/images-books/archive/) | Building records and photos | Sample pages seen | Link; check image rights item by item |
| [Heritage Gateway](https://www.heritagegateway.org.uk/) | Historic environment records | Not yet checked | Directory |
| [OS OpenData](https://osdatahub.os.uk/) | Modern UK reference geography | — | Modern context only |
| [OpenStreetMap](https://www.openstreetmap.org/) | Modern map/geocoding | ODbL attribution | Base map context |
| Berkshire Record Office | Licensing records, local archives | Catalogue pages only | **Contact as launch partner** |
| West Berkshire Museum | Local objects and photos | Not yet contacted | **Contact as launch partner** |
| [Pub Wiki](https://pubwiki.co.uk/Berkshire/Newbury/Pigeons.shtml) | Pub, licensee and census histories | Page read; reuse not confirmed | Link; invite as contributor |
| [Closed Pubs](https://www.closedpubs.co.uk/berkshire/newbury_pigeons.html) | Lost pub listings and photos | Page read; reuse not confirmed | Link; invite as contributor |
| [Nick's local history blog](https://nickbits.co.uk/) | Newbury pub research | Page read | Invite as an early historian |

**Berkshire/Newbury source pack (pilot):** Berkshire Record Office, local history societies, historic OS maps, town directories, FreeREG/FreeCEN coverage, newspaper and photo catalogues. Partner outreach beats speculative scraping.

## Reviewed and deprioritised

| Item | Reason |
|---|---|
| GB Places | Modern OS data; no help with historic names |
| Harmonised country-of-birth datasets | 1971–2011 aggregate statistics, not people |
| OpenHistoricalMap/data repo | Last updated 2021; no root licence file (the OHM service itself is still a candidate) |
| Voices of Authority | Last updated 2018; no root licence file |
| rOpenGov/oldbailey | Too specialised for v1 |
| biolineage | Smaller project; review before relying on it |
