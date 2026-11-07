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
| [National Heritage List for England](https://historicengland.org.uk/listing/the-list/) (Historic England) | Every listed building in England: grade, listing date, exact location (146 in central Newbury) | Live ArcGIS service | Full copy (OGL) | 2026-11-07 | Add a town to search near it. Listing date isn't build date (ADR-035) |
| [The Gazette](https://www.thegazette.co.uk/) | Official notices since 1665: commissions, honours, bankruptcies, partnerships, deceased estates | Live JSON search | Link and label | 2026-11-07 | Notices at least 100 years old only, so living people stay out; at most one request every 2 seconds (ADR-035) |

## 2. Built, waiting for a key or access

All switch on from `services/api/.env`. Setup steps in [CONNECTORS.md](CONNECTORS.md).

| Source | What it gives | Key or access | Storing | Tested live | Terms to know |
|---|---|---|---|---|---|
| [Europeana](https://www.europeana.eu/) | 50m+ items from European institutions | **Project** API key (`EUROPEANA_API_KEY`) | Metadata (CC0) | Yes (demo key) | Personal keys not for production; media rights per item |
| [The National Archives: Discovery](https://discovery.nationalarchives.gov.uk/) | Catalogues of TNA and ~2,500 UK archives, incl. Royal Berkshire Archives | Register server IP by email (`TNA_DISCOVERY_ENABLED`) | **None** | Yes | No caching or storing; ≤3,000 calls a day, 1 a second |
| [Geograph](https://www.geograph.org.uk/) | Located photos of Britain, mostly since 2005 | Free key (`GEOGRAPH_API_KEY`) | Link only | Yes | CC BY-SA 2.0; credit photographer; no bulk use |
| [OS Names API](https://osdatahub.os.uk/) | Today's places, streets, postcodes with locations | Free OS Data Hub key (`OS_DATA_HUB_KEY`) | Full copy (OGL) | No | Attribution line required |
| [GeoNames](https://www.geonames.org/) | Place names worldwide, other spellings, locations | Free account name (`GEONAMES_USERNAME`) | Full copy (CC BY) | No | Commercial use allowed; 10,000 credits a day |
| [DigitalNZ](https://digitalnz.org/) incl. Papers Past | NZ newspapers, photos, archives | Key (`DIGITALNZ_API_KEY`) | Link only | Yes | Commercial use only with key, selected metadata; 10,000 calls a day |
| [Trove](https://trove.nla.gov.au/) | Australian newspapers 1803–1950s | Key (`TROVE_API_KEY`) **plus NLA permission for commercial use** | Link only | No | Keys expire yearly |
| [DPLA](https://dp.la/) | US libraries, archives, museums | Key by email (`DPLA_API_KEY`) | Metadata (CC0) | No | Terms page not yet read in full |

## 3. Maps and places

| Service | Use | Key? | Status | Terms and notes |
|---|---|---|---|---|
| [OpenFreeMap](https://openfreemap.org/) | Today's map on the time map | No | **Live** | Free, commercial use allowed; OSM attribution shown |
| [NLS historic OS maps](https://maps.nls.uk/) via [MapTiler](https://www.maptiler.com/) | Historic layers 1888–1961 | Yes (`MAPTILER_KEY`) | **Built, needs key** | Maps CC BY 3.0 (credit NLS); MapTiler free plan is non-commercial. Ask NLS to confirm commercial use (see partners) |
| [NLS Data Foundry map collections](https://data.nls.uk/tools/maps-and-tools/) | 220,000+ map images incl. 19th–20th century OS maps of England; a paid API for more detailed maps | Varies | Partner | Rights page not read |
| NLS historical boundary viewer | Parish and county boundaries as they were | Not checked | Candidate | Would let records sit in the parish of their day |
| [Historic England Open Data Hub](https://historicengland.org.uk/listing/the-list/open-data-hub/) (other layers) | Scheduled monuments, parks and gardens, battlefields, conservation areas, Heritage at Risk, aerial archaeology mapping | No | Candidate | OGL. Same ArcGIS service as the listed buildings connector, so quick to add |
| [Historic England Aerial Explorer](https://historicengland.org.uk/images-books/archive/collections/aerial-photos/) | 540,000+ aerial photos by place and date | — | Link out | Image rights to check |
| [Britain from Above](https://britainfromabove.org.uk/) | Aerial photos 1919–1953 | — | Partner | Images bought or licensed |
| [Old Maps Online](https://www.oldmapsonline.org/) | Search old maps by place across many libraries | Not checked | Link out | Discovery tool |
| [Know Your Place](https://www.kypwest.org.uk/) | Community historic map layers | — | Link out | Some areas of England only; Berkshire coverage to check |
| [World Historical Gazetteer](https://whgazetteer.org/) | Historical places and name variants | No | **Not allowed** for now | Default licence CC BY-NC (non-commercial); individual datasets vary. Ask them |
| [openstreetmap.org tiles](https://operations.osmfoundation.org/policies/tiles/) | — | No | **Not allowed** for us | Policy warns commercial users access can be withdrawn; no heavy use |
| [OpenHistoricalMap](https://www.openhistoricalmap.org/) | Map data with dates | No | Candidate | Licence and Newbury coverage not checked |
| [Allmaps](https://allmaps.org/) | Aligning scanned local maps to today's map | No | Candidate | Code licence not found; check |

## 4. Open APIs we could connect (no key, not built)

| Source | What it gives | Why it's useful | Terms and notes |
|---|---|---|---|
| [Wikimedia Commons](https://commons.wikimedia.org/) | Photos and scans, each with its own licence, often located and dated | Pictures of places and people on the map | Per-file licences; API terms not yet checked |
| [Internet Archive](https://archive.org/) | Books, directories, local histories, some newspapers | Trade directories (Kelly's etc.) are key evidence for addresses and licensees | Item-level rights; use the HTTP API (their Python library is AGPL) |
| [Library of Congress](https://www.loc.gov/apis/) | Photos, maps, manuscripts, US newspapers 1770–1963, with IIIF | Emigrant relatives; images | **Blocked our server** with a bot challenge (7 Nov 2026). Ask LoC, or test from the production server |
| [Archives Hub](https://archiveshub.jisc.ac.uk/) | UK university and specialist archive catalogues | Collections TNA may not cover | Interface and terms not checked |
| [Archaeology Data Service](https://archaeologydataservice.ac.uk/) | Excavation archives, reports, spatial data | Archaeology near a place | No general search API yet, only SPARQL; collections vary |
| [UK Parliament / Historic Hansard](https://developer.parliament.uk/) | Debates, members | Local MPs, petitions, events | Not checked |
| [Old Bailey Online](https://www.oldbaileyonline.org/) | London trials 1674–1913 | Relatives who went to London | Not checked |
| [Science Museum Group](https://collection.sciencemuseumgroup.org.uk/) | Objects and photos | Context | Not checked |
| [Wellcome Collection](https://wellcomecollection.org/) | Medical history, photos, archives | Explaining old illnesses and institutions | Not checked |
| [Postcodes.io](https://postcodes.io/) | Postcode to location | Placing modern addresses | Open source; data from ONS/OS; not checked |
| [Nominatim](https://nominatim.org/) (OpenStreetMap) | Address search | Placing addresses | Strict usage policy (max one request a second, no heavy use); not checked |

## 5. APIs that need a key or approval, not built

| Source | What it gives | Status | Notes |
|---|---|---|---|
| [FamilySearch](https://www.familysearch.org/developers/) | World's largest free genealogy collection | **Not allowed** for now | API closed to the public; Innovator Program application, compatibility review and signed agreements needed |
| [Transkribus](https://docs.transkribus.org/) | Specialist handwriting recognition | Candidate | Processing service, not a source: API in beta and needs a paid plan. Would sit beside Claude for handwriting jobs |
| [Smithsonian Open Access](https://www.si.edu/openaccess) | US museum objects and images | Candidate | Key from api.data.gov; terms not checked |
| [Rijksmuseum](https://data.rijksmuseum.nl/) | Dutch art and objects | Candidate | Key and terms not checked; low relevance to Newbury |
| [US National Archives catalog](https://www.archives.gov/research/catalog) | US federal records | Candidate | Not checked |
| [Commonwealth War Graves Commission](https://www.cwgc.org/) | War dead and cemeteries | Candidate | No public API known; data access to check |
| [BillionGraves](https://billiongraves.com/) | Gravestone photos and transcriptions | Candidate | Partner API not checked |

## 6. Downloadable datasets

| Dataset | What it gives | Status | Terms |
|---|---|---|---|
| GB1900 raw dump | Old map names | **Live** (hosted) | CC0 |
| [OS OpenData](https://osdatahub.os.uk/) | Modern boundaries, roads, names | Candidate | OGL |
| [Vision of Britain / GBHDB](https://www.visionofbritain.org.uk/) | Historical statistics and boundaries | Candidate | Statistics open; parish boundaries commercially licensed |
| [HISCO](https://iisg.amsterdam/en/data/data-websites/history-of-work) | Codes and descriptions of historical occupations | Candidate | Licence not checked. Would power "what did this job mean?" |
| Bank of England "A millennium of macroeconomic data" | Prices and wages over centuries | Candidate | Licence not checked. Never present an average as an ancestor's wage |
| [UK Data Service](https://ukdataservice.ac.uk/) | Historical census and population data | Candidate | Registration; some controlled access |
| [I-CeM](https://www.essex.ac.uk/research-projects/integrated-census-microdata) | ~230m census person records 1851–1921 | Not allowed (for now) | Names and addresses need a special licence |
| [British Library datasets](https://bl.iro.bl.uk/) | Some newspaper and book text | Candidate | Licence per item |
| [Living with Machines (LwMDB)](https://www.lancaster.ac.uk/) | 19th-century newspaper metadata | Candidate | Code MIT; data licence to confirm |
| Geograph data dumps | All Geograph photo metadata | Candidate | Their route for bulk use (not the live API) |
| [Canmore](https://canmore.org.uk/) (Scotland), [Coflein](https://coflein.gov.uk/) (Wales) | National historic environment records | Candidate | Outside the pilot area |

## 7. Websites we link to (no API, or reuse not allowed)

| Website | What it holds | Why link only |
|---|---|---|
| [Free UK Genealogy](https://www.freeukgenealogy.org.uk/) (FreeBMD, FreeCEN, FreeREG) | Birth, marriage and death indexes; census; parish registers | No API; data sharing not started (also a partner, below) |
| [General Register Office](https://www.gro.gov.uk/) | Official certificates | Ordering service only |
| [Findmypast](https://www.findmypast.co.uk/) | Census, parish, military, 1921 census, newspapers | Commercial; no reusable API (also a partner) |
| [Ancestry](https://www.ancestry.co.uk/) | Census, parish, military, trees | Commercial; no reusable API. Users can import their own GEDCOM |
| [Find a Grave](https://www.findagrave.com/) | Gravestones, burials, memorial photos | Owned by Ancestry; no reusable API |
| [Deceased Online](https://www.deceasedonline.com/) | UK burial and cremation registers | Commercial |
| [British Newspaper Archive](https://www.britishnewspaperarchive.co.uk/) | British and Irish newspapers, likely incl. Reading Mercury and Newbury Weekly News | Run by Findmypast; no API; licensing only |
| [ScotlandsPeople](https://www.scotlandspeople.gov.uk/) | Scottish records | Pay per record |
| [National Archives of Ireland](https://www.nationalarchives.ie/), [IrishGenealogy.ie](https://www.irishgenealogy.ie/) | Irish census and civil records | Not checked |
| [The Workhouse](https://www.workhouses.org.uk/) | Every workhouse and Poor Law Union, rules, staff, Acts | Private site: link, or ask permission (partner) |
| [GENUKI](https://www.genuki.org.uk/) | County and parish guides to what records survive and where | Volunteer site: link, or ask permission (partner) |
| [Connected Histories](https://www.connectedhistories.org/) | One search across many British history resources | Not checked |
| [History of Parliament Online](https://www.historyofparliamentonline.org/) | MPs' biographies, constituencies | Not checked |
| [Cambridge Core](https://www.cambridge.org/core/), [JSTOR](https://www.jstor.org/) | Academic history | Subscription |
| [Bank of England inflation calculator](https://www.bankofengland.co.uk/monetary-policy/inflation/inflation-calculator) | Old money in today's terms | Link; or use their dataset (section 6) |
| [Pub Wiki](https://pubwiki.co.uk/), [Closed Pubs](https://www.closedpubs.co.uk/), [Nickbits blog](https://nickbits.co.uk/) | Pub and licensee histories | Reuse not confirmed; we store checked facts in our own words (ADR-018) and invite them as contributors |
| [Historic England Archive](https://historicengland.org.uk/images-books/archive/) | Building records and photos | Image rights item by item |
| [Heritage Gateway](https://www.heritagegateway.org.uk/) | Historic environment records | Not checked |
| [British History Online](https://www.british-history.ac.uk/) | Victoria County History and more | Free and premium sections |
| [Lives of the First World War](https://livesofthefirstworldwar.iwm.org.uk/), [IWM collections](https://www.iwm.org.uk/collections), [A Street Near You](https://astreetnearyou.org/) | First World War lives, photos, oral history | Not checked |
| [National Army Museum](https://www.nam.ac.uk/collections) | Regimental collections | Not checked |
| [British Pathé](https://www.britishpathe.com/) | Newsreels | Footage needs a paid licence; search and link only |
| [BFI Player](https://player.bfi.org.uk/) and Britain on Film | Film, incl. films mapped to places | Embedding not allowed; link only |
| [BBC Archive](https://www.bbc.co.uk/archive) | Broadcast material | Link only |
| [Welsh Newspapers Online](https://newspapers.library.wales/) | Welsh newspapers | Rights not checked |
| [HathiTrust](https://www.hathitrust.org/), [Project Gutenberg](https://www.gutenberg.org/), [Google Books](https://books.google.com/), [Oxford Text Archive](https://ota.bodleian.ox.ac.uk/) | Books and texts | Rights vary by item and country |
| [Archives Portal Europe](https://www.archivesportaleurope.net/), [British Library](https://www.bl.uk/) | Catalogues | Later |

## 8. Partners to approach

Local material that isn't online at all is likely to matter most. Owner: the ArchiveHub owner unless noted.

| Organisation | What they could offer | Status |
|---|---|---|
| Berkshire Record Office (Royal Berkshire Archives) | Licensing records, deeds, sale particulars; catalogue already visible via TNA Discovery | Not contacted; **launch partner** |
| West Berkshire Museum | Local objects and photos | Not contacted; **launch partner** |
| West Berkshire Historic Environment Record | Local archaeology and historic buildings | Not contacted |
| Newbury Library local studies | Directories, maps, cuttings, photos | Not contacted |
| Reading Central Library local studies | Directories, maps, cuttings | Not contacted |
| Newbury Weekly News | Local newspaper archive | Not contacted |
| Berkshire Family History Society | Burial and memorial indexes, local expertise | Not contacted |
| Local history societies (e.g. Newbury District Field Club) | Research, photos, members as early historians | Not contacted |
| Wessex Film and Sound Archive | Regional film and sound, possibly covering Berkshire | Not contacted |
| National Library of Scotland | Confirmation of commercial use of their historic maps; Data Foundry maps | Not contacted; **ask early**, the time map depends on it |
| The Workhouse (site owner) | Permission to draw on workhouse and Poor Law pages | Not contacted |
| GENUKI | Permission to draw on parish guides | Not contacted |
| Free UK Genealogy | FreeBMD, FreeCEN, FreeREG data | Not contacted |
| University of Leicester (Historical Directories of England and Wales) | Digitised trade directories | Terms not checked |
| Historic England: Britain from Above | Aerial photos 1919–1953 | Licensing not checked |
| World Historical Gazetteer (University of Pittsburgh) | Commercial use of its data | Not contacted |
| Library of Congress | API access from our server | Not contacted |
| Findmypast | British Newspaper Archive licensing | Not contacted; possible competitor |
| Pub Wiki, Closed Pubs, Nickbits | Pub histories | Invite as contributors |
| The National Archives | Discovery API access | Registration email still to send |
| National Library of Australia | Commercial use of Trove | Permission to request |

## 9. Programs and code libraries

Full licences in [DEPENDENCIES.md](DEPENDENCIES.md). Only the ones that bring data in, read it or match it are listed here.

| Program | Use | Status | Licence |
|---|---|---|---|
| faster-whisper | Interview transcription | **In use** | MIT |
| MapLibre GL JS | Time map | **In use** | BSD-3 |
| pypdf | Reading PDF text | **In use** | BSD-3 |
| Tesseract | Printed-text OCR | Supported, not installed | Apache-2.0 |
| Claude (Anthropic API) | Assistant, handwriting, interview notes | **In use** | Commercial API |
| Topola / family-chart | Drawing family trees | Planned | Apache-2.0 / MIT |
| OpenSeadragon, Mirador, Universal Viewer | Zooming and comparing scans (IIIF) | Planned | BSD-3 / Apache-2.0 / MIT |
| Docling, Kraken, OCRmyPDF | Better document reading, historical handwriting | Planned | MIT / Apache-2.0 / MPL-2.0 |
| eScriptorium | Shared transcription and correction | Candidate | Licence to check |
| Zotero Web API | Importing historians' research libraries and citations (WP7) | Candidate | Service API; free with the user's own key |
| Nomenklatura, Rigour, Yente | Recording "same / different / undecided" decisions about people, name normalisation, matching | Candidate | Licences to check |
| Dedupe | Suggesting possible duplicates (never merging on its own) | Candidate | MIT (check) |
| OpenRefine | Cleaning and reconciling partner datasets (internal) | Candidate | BSD-3 |
| MapReader | Reading features from scanned maps | Candidate | MIT |
| OpenLayers | Historic map overlays (WMS/WMTS) if MapLibre isn't enough | Candidate | BSD-2 (check) |
| PMTiles, Planetiler | Hosting our own map tiles | Candidate | BSD-3 / Apache-2.0 (check) |
| QGIS | Preparing boundaries and georeferencing (internal desktop tool) | Candidate | GPL: internal use only, never in our code |
| Wikibase Suite | Hosting our own knowledge graph | Candidate | GPL: run separately only after review |
| ArchiveBox, Heritrix | Capturing historians' old websites before migration (WP7) | Candidate | MIT / Apache-2.0 |
| Gramps, webtrees, Omeka S, AtoM, Archivematica, Discourse and other GPL/AGPL projects | Design reference only | **Not used in the core** | GPL / AGPL |

---

## Changing this list

When a source changes status, update its row here and, where relevant: [DATA_SOURCES.md](DATA_SOURCES.md), `services/api/history/data/sources.json` (the in-product source directory), [CONNECTORS.md](CONNECTORS.md) for keyed connectors, and an ADR in [DECISIONS.md](DECISIONS.md) for anything affecting data rights.
