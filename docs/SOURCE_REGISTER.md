# Source register

**The running list of every connector, database, website and program ArchiveHub uses or could use.** Update it whenever a source is connected, checked, contacted or ruled out, and change "Last checked" when you do.

- Terms and access details are **provisional** until re-read and, where needed, legally confirmed. "Not checked" means nobody has read the terms yet; don't build on it.
- Details live elsewhere: [DATA_SOURCES.md](DATA_SOURCES.md) (research notes and scores), [CONNECTORS.md](CONNECTORS.md) (how to switch on keyed connectors), [DEPENDENCIES.md](DEPENDENCIES.md) (software licences), [DECISIONS.md](DECISIONS.md) (why).
- **Storing:** what we may keep follows each source's terms. "None" means results are shown live and never saved.

**Status key**

| Status | Meaning |
|---|---|
| **Live** | Connected and working now |
| **Built, needs key** | Connector written; switches on when a key or access is set |
| **Candidate** | Has an API or download we could connect; not built yet |
| **Link out** | No usable API, or terms don't allow reuse; we point people to it |
| **Partner** | Best reached by agreement with the holder |
| **Not allowed** | Terms or access rule it out for now |

Last full review: 7 Nov 2026.

---

## 1. Connected now (no key needed)

| Source | What it gives | How | Storing | Last checked | Notes |
|---|---|---|---|---|---|
| ArchiveHub checked records | Hand-checked Cheap Street facts with links | Hosted (our own wording) | Our facts and a link | 2026-11-05 | ADR-018 |
| Old map names (OS six-inch, c.1900) | 15,188 map labels for Newbury and West Berkshire, with locations | Hosted, from the GB1900 raw dump (CC0) | Full copy | 2026-11-05 | Must not be called "GB1900" (ADR-021) |
| [Wikidata](https://www.wikidata.org/) | People, places, organisations | Live API | Full copy (CC0) | 2026-11-05 | Context, not proof |

## 2. Built, waiting for a key or access

All switch on from `services/api/.env`. Setup steps in [CONNECTORS.md](CONNECTORS.md).

| Source | What it gives | Key or access | Storing | Tested live | Terms to know |
|---|---|---|---|---|---|
| [Europeana](https://www.europeana.eu/) | 50m+ items from European institutions | **Project** API key (`EUROPEANA_API_KEY`) | Metadata (CC0) | Yes (demo key) | Personal keys not for production; media rights per item |
| [The National Archives: Discovery](https://discovery.nationalarchives.gov.uk/) | Catalogues of TNA and ~2,500 UK archives, incl. Royal Berkshire Archives | Register server IP by email (`TNA_DISCOVERY_ENABLED`) | **None** | Yes | No caching or storing; ≤3,000 calls a day, 1 a second |
| [Geograph](https://www.geograph.org.uk/) | Located photos of Britain, mostly since 2005 | Free key (`GEOGRAPH_API_KEY`) | Link only | Yes | CC BY-SA 2.0; credit photographer; no bulk use |
| [OS Names API](https://osdatahub.os.uk/) | Today's places, streets, postcodes with locations | Free OS Data Hub key (`OS_DATA_HUB_KEY`) | Full copy (OGL) | No | Attribution line required |
| [DigitalNZ](https://digitalnz.org/) incl. Papers Past | NZ newspapers, photos, archives | Key (`DIGITALNZ_API_KEY`) | Link only | Yes | Commercial use only with key, selected metadata; 10,000 calls a day |
| [Trove](https://trove.nla.gov.au/) | Australian newspapers 1803–1950s | Key (`TROVE_API_KEY`) **plus NLA permission for commercial use** | Link only | No | Keys expire yearly |
| [DPLA](https://dp.la/) | US libraries, archives, museums | Key by email (`DPLA_API_KEY`) | Metadata (CC0) | No | Terms page not yet read in full |

## 3. Map services

| Service | Use | Key? | Status | Terms |
|---|---|---|---|---|
| [OpenFreeMap](https://openfreemap.org/) | Today's map on the time map | No | **Live** | Free, commercial use allowed; OSM attribution shown |
| [NLS historic OS maps](https://maps.nls.uk/) via [MapTiler](https://www.maptiler.com/) | Historic layers 1888–1961 | Yes (`MAPTILER_KEY`) | **Built, needs key** | Maps CC BY 3.0 (credit NLS); MapTiler free plan is non-commercial, paid plan before launch |
| [openstreetmap.org tiles](https://operations.osmfoundation.org/policies/tiles/) | — | No | **Not allowed** for us | Policy warns commercial users access can be withdrawn; no heavy use |
| [OpenHistoricalMap](https://www.openhistoricalmap.org/) | Map data with dates | No | Candidate | Licence and Newbury coverage not checked |
| [Allmaps](https://allmaps.org/) | Aligning scanned local maps to today's map | No | Candidate | Code licence not found; check |

## 4. Open APIs we could connect (no key, not built)

| Source | What it gives | Why it's useful | Terms |
|---|---|---|---|
| [Wikimedia Commons](https://commons.wikimedia.org/) | Photos and scans, each with its own licence, often located and dated | Pictures of places and people on the map | Per-file licences; API terms not yet checked |
| [Internet Archive](https://archive.org/) | Books, directories, local histories, some newspapers | Trade directories (Kelly's etc.) are key evidence for addresses and licensees | Item-level rights; use the HTTP API (their Python library is AGPL) |
| [Historic England: National Heritage List](https://historicengland.org.uk/listing/the-list/) | Listed buildings with locations and descriptions | Cheap Street's actual buildings on the map | Open data terms not checked |
| [Chronicling America / loc.gov](https://www.loc.gov/apis/) | US newspapers 1770–1963 | Emigrant relatives | Not checked |
| [Archives Hub](https://archiveshub.jisc.ac.uk/) | UK university and specialist archive catalogues | Collections TNA may not cover | Interface and terms not checked |
| [UK Parliament / Historic Hansard](https://developer.parliament.uk/) | Debates, members | Local MPs, petitions, events | Not checked |
| [Old Bailey Online](https://www.oldbaileyonline.org/) | London trials 1674–1913 | Relatives who went to London | Not checked |
| [Science Museum Group](https://collection.sciencemuseumgroup.org.uk/) | Objects and photos | Context | Not checked |
| [Wellcome Collection](https://wellcomecollection.org/) | Medical history, photos, archives | Context | Not checked |
| [Postcodes.io](https://postcodes.io/) | Postcode to location | Placing modern addresses | Open source; data from ONS/OS; not checked |
| [Nominatim](https://nominatim.org/) (OpenStreetMap) | Address search | Placing addresses | Strict usage policy (max one request a second, no heavy use); not checked |

## 5. APIs that need a key, not built

| Source | What it gives | Status | Notes |
|---|---|---|---|
| [FamilySearch](https://www.familysearch.org/developers/) | World's largest free genealogy collection | **Not allowed** for now | API closed to the public; Innovator Program application, compatibility review and signed agreements needed |
| [Smithsonian Open Access](https://www.si.edu/openaccess) | US museum objects and images | Candidate | Key from api.data.gov; terms not checked |
| [Rijksmuseum](https://data.rijksmuseum.nl/) | Dutch art and objects | Candidate | Key and terms not checked; low relevance to Newbury |
| [US National Archives catalog](https://www.archives.gov/research/catalog) | US federal records | Candidate | Not checked |
| [Commonwealth War Graves Commission](https://www.cwgc.org/) | War dead and cemeteries | Candidate | No public API known; data access to check |

## 6. Downloadable datasets

| Dataset | What it gives | Status | Terms |
|---|---|---|---|
| GB1900 raw dump | Old map names | **Live** (hosted) | CC0 |
| [OS OpenData](https://osdatahub.os.uk/) | Modern boundaries, roads, names | Candidate | OGL |
| [Vision of Britain / GBHDB](https://www.visionofbritain.org.uk/) | Historical statistics and boundaries | Candidate | Statistics open; parish boundaries commercially licensed |
| [I-CeM](https://www.essex.ac.uk/research-projects/integrated-census-microdata) | ~230m census person records 1851–1921 | Not allowed (for now) | Names and addresses need a special licence |
| [British Library datasets](https://bl.iro.bl.uk/) | Some newspaper and book text | Candidate | Licence per item |
| [Living with Machines (LwMDB)](https://www.lancaster.ac.uk/) | 19th-century newspaper metadata | Candidate | Code MIT; data licence to confirm |
| Geograph data dumps | All Geograph photo metadata | Candidate | Their route for bulk use (not the live API) |

## 7. Websites we link to (no API, or reuse not allowed)

| Website | What it holds | Why link only |
|---|---|---|
| [Free UK Genealogy](https://www.freeukgenealogy.org.uk/) (FreeBMD, FreeCEN, FreeREG) | Birth, marriage and death indexes; census; parish registers | No API; data sharing not started (also a partner, below) |
| [General Register Office](https://www.gro.gov.uk/) | Official certificates | Ordering service only |
| [Findmypast](https://www.findmypast.co.uk/) | Census, parish, military, 1921 census, newspapers | Commercial; no reusable API (also a partner) |
| [Ancestry](https://www.ancestry.co.uk/) | Census, parish, military, trees | Commercial; no reusable API. Users can import their own GEDCOM |
| [British Newspaper Archive](https://www.britishnewspaperarchive.co.uk/) | British and Irish newspapers, likely incl. Reading Mercury and Newbury Weekly News | Run by Findmypast; no API; licensing only |
| [ScotlandsPeople](https://www.scotlandspeople.gov.uk/) | Scottish records | Pay per record |
| [National Archives of Ireland](https://www.nationalarchives.ie/), [IrishGenealogy.ie](https://www.irishgenealogy.ie/) | Irish census and civil records | Not checked |
| [Pub Wiki](https://pubwiki.co.uk/), [Closed Pubs](https://www.closedpubs.co.uk/), [Nickbits blog](https://nickbits.co.uk/) | Pub and licensee histories | Reuse not confirmed; we store checked facts in our own words (ADR-018) and invite them as contributors |
| [Historic England Archive](https://historicengland.org.uk/images-books/archive/) | Building records and photos | Image rights item by item |
| [Heritage Gateway](https://www.heritagegateway.org.uk/) | Historic environment records | Not checked |
| [British History Online](https://www.british-history.ac.uk/) | Victoria County History and more | Free and premium sections |
| [Lives of the First World War](https://livesofthefirstworldwar.iwm.org.uk/), [IWM collections](https://www.iwm.org.uk/collections), [A Street Near You](https://astreetnearyou.org/) | First World War lives, photos, oral history | Not checked |
| [BFI Player](https://player.bfi.org.uk/) | Film | Embedding not allowed; link only |
| [Welsh Newspapers Online](https://newspapers.library.wales/) | Welsh newspapers | Rights not checked |
| [HathiTrust](https://www.hathitrust.org/), [Project Gutenberg](https://www.gutenberg.org/), [Google Books](https://books.google.com/), [Oxford Text Archive](https://ota.bodleian.ox.ac.uk/) | Books and texts | Rights vary by item and country |
| [Archives Portal Europe](https://www.archivesportaleurope.net/), [British Library](https://www.bl.uk/) | Catalogues | Later |

## 8. Partners to approach

Local material that isn't online at all is likely to matter most. Owner: the ArchiveHub owner unless noted.

| Organisation | What they could offer | Status |
|---|---|---|
| Berkshire Record Office (Royal Berkshire Archives) | Licensing records, deeds, sale particulars; catalogue already visible via TNA Discovery | Not contacted; **launch partner** |
| West Berkshire Museum | Local objects and photos | Not contacted; **launch partner** |
| Newbury Weekly News | Local newspaper archive | Not contacted |
| Berkshire Family History Society | Burial and memorial indexes, local expertise | Not contacted |
| Reading Central Library local studies | Directories, maps, cuttings | Not contacted |
| Free UK Genealogy | FreeBMD, FreeCEN, FreeREG data | Not contacted |
| University of Leicester (Historical Directories of England and Wales) | Digitised trade directories | Terms not checked |
| Historic England: Britain from Above | Aerial photos 1919–1953 | Licensing not checked |
| Findmypast | British Newspaper Archive licensing | Not contacted; possible competitor |
| Pub Wiki, Closed Pubs, Nickbits | Pub histories | Invite as contributors |
| The National Archives | Discovery API access | Registration email still to send |
| National Library of Australia | Commercial use of Trove | Permission to request |

## 9. Programs and code libraries

Full licences in [DEPENDENCIES.md](DEPENDENCIES.md). Only the ones that bring data in or read it are listed here.

| Program | Use | Status | Licence |
|---|---|---|---|
| faster-whisper | Interview transcription | **In use** | MIT |
| MapLibre GL JS | Time map | **In use** | BSD-3 |
| pypdf | Reading PDF text | **In use** | BSD-3 |
| Tesseract | Printed-text OCR | Supported, not installed | Apache-2.0 |
| Claude (Anthropic API) | Assistant, handwriting, interview notes | **In use** | Commercial API |
| Topola / family-chart | Drawing family trees | Planned | Apache-2.0 / MIT |
| OpenSeadragon, Mirador | Zooming and comparing scans (IIIF) | Planned | BSD-3 / Apache-2.0 |
| Docling, Kraken, OCRmyPDF | Better document reading, historical handwriting | Planned | MIT / Apache-2.0 / MPL-2.0 |
| MapReader | Reading features from scanned maps | Candidate | MIT |
| OpenRefine | Cleaning partner datasets (internal) | Candidate | BSD-3 |
| ArchiveBox, Heritrix | Capturing historians' old websites before migration (WP7) | Candidate | MIT / Apache-2.0 |
| Gramps, webtrees, Omeka S, AtoM, Archivematica, Discourse and other GPL/AGPL projects | Design reference only | **Not used in the core** | GPL / AGPL |

---

## Changing this list

When a source changes status, update its row here and, where relevant: [DATA_SOURCES.md](DATA_SOURCES.md), `services/api/history/data/sources.json` (the in-product source directory), [CONNECTORS.md](CONNECTORS.md) for keyed connectors, and an ADR in [DECISIONS.md](DECISIONS.md) for anything affecting data rights.
