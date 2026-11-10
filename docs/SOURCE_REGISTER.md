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
| Old map names (OS six-inch, c.1900) | Map labels across Great Britain, with locations (the West Berkshire pilot was 15,188) | Hosted, from the GB1900 raw dump (CC0) | Full copy | 2026-11-10 | Must not be called "GB1900" (ADR-021) |
| [Wikidata](https://www.wikidata.org/) | People, places, organisations | Live API | Full copy (CC0) | 2026-11-05 | Context, not proof |
| [National Heritage List for England](https://historicengland.org.uk/listing/the-list/) (Historic England) | Every listed building in England: grade, listing date, exact location (146 in central Newbury) | Live ArcGIS service | Full copy (OGL) | 2026-11-07 | Add a town to search near it. Listing date isn't build date (ADR-035) |
| [Historic Environment Scotland](https://portal.historicenvironment.scot/) listed buildings | Every listed building in Scotland: category, date designated, location | Live ArcGIS MapServer | Shown live (OGL) | 2026-11-10 | Time map layer, with the HES credit. The service doesn't page, so results are cut at the map's limit (ADR-043) |
| [Cadw](https://cadw.gov.wales/) listed buildings (via DataMapWales) | Every listed building in Wales: grade, date designated, location, report link | Live WFS | Shown live (OGL) | 2026-11-10 | Time map layer, with the Cadw credit (ADR-043) |
| [Listed Buildings Northern Ireland](https://www.opendatani.gov.uk/dataset/listed-buildings-northern-ireland) (Department for Communities, Historic Environment Division) | 9,201 listed buildings: grade (A to B2), address, date range built, location | Hosted, from the monthly Open Data NI GeoJSON (Irish Grid, converted) | Full copy (OGL) | 2026-11-10 | `import_ni_listed_buildings`. "Record Only" and delisted entries left out. DfC's ArcGIS service is for its own viewer, so we use the open download (ADR-046) |
| Protected areas (Historic Environment Scotland) | Conservation areas (from the local authorities), scheduled monuments, gardens and designed landscapes, Inventory battlefields, as outlines | Live ArcGIS MapServers | Shown live, cached a day (OGL v3, HES credit) | 2026-11-10 | Time map layer (ADR-047). HES: "indicative only; refer to the legal documentation" |
| Protected areas (Wales, via DataMapWales) | Scheduled monuments and registered historic parks and gardens (Cadw); conservation areas (Welsh Government, from local planning authorities) | Live WFS | Shown live, cached a day (OGL, Cadw credit) | 2026-11-10 | Time map layer (ADR-047). Wales has no battlefields layer here |
| [The Gazette](https://www.thegazette.co.uk/) | Official notices since 1665: commissions, honours, bankruptcies, partnerships, deceased estates | Live JSON search | Link and label | 2026-11-07 | Notices at least 100 years old only, so living people stay out; at most one request every 2 seconds (ADR-035) |
| Protected areas (Historic England) | Conservation areas, scheduled monuments, parks and gardens, battlefields, as outlines | Live ArcGIS services | Shown live, cached a day (OGL) | 2026-11-07 | Time map layer (ADR-039) |
| Glossary sources: [NLS OS abbreviations](https://maps.nls.uk/os/abbrev/), [Nottingham: Money](https://www.nottingham.ac.uk/manuscriptsandspecialcollections/researchguidance/weightsandmeasures/money.aspx), [TNA: Poverty and the Poor Laws](https://www.nationalarchives.gov.uk/help-with-your-research/research-guides/poverty-poor-laws), [Nottingham: Dating documents](https://www.nottingham.ac.uk/manuscriptsandspecialcollections/researchguidance/datingdocuments/introduction.aspx), [TNA: Wills 1384–1858](https://www.nationalarchives.gov.uk/help-with-your-research/research-guides/wills-1384-1858/), [Church of England: Reading of banns](https://www.churchofengland.org/life-events/your-church-wedding/planning-your-ceremony/reading-banns), [PRONI: The Townland](https://www.proni.gov.uk/files/proni/2025-12/Local%20History%20Series%201%20-%20The%20Townland.pdf) (7 entries added 2026-11-10) | Checked explanations, in our own words | Hosted (our wording, with links) | Our facts and a link | 2026-11-07 | ADR-039 |
| [The Metropolitan Museum of Art](https://www.metmuseum.org/art/collection) | ~500,000 objects; images for public-domain ones | Live API | Full copy (CC0) | 2026-11-07 | Context: what things of a period looked like |
| [Art Institute of Chicago](https://www.artic.edu/collection) | ~130,000 artworks and objects | Live API | Full copy (CC0) | 2026-11-07 | Their descriptions are CC BY, so we don't fetch them |
| [OpenAlex](https://openalex.org/) | 250m+ academic articles, books, theses | Live API | Full copy (CC0 metadata) | 2026-11-07 | Works without a key on a small shared budget; set `OPENALEX_API_KEY` (free) for production |

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

## 5. APIs that need a key or approval, not built (the key list)

| Source | What it gives | Status | Notes |
|---|---|---|---|
| [FamilySearch](https://www.familysearch.org/developers/) | World's largest free genealogy collection | **Not allowed** for now | API closed to the public; Innovator Program application, compatibility review and signed agreements needed |
| [Transkribus](https://docs.transkribus.org/) | Specialist handwriting recognition | Candidate | Processing service, not a source: API in beta and needs a paid plan. Would sit beside Claude for handwriting jobs |
| [Smithsonian Open Access](https://www.si.edu/openaccess) | US museum objects and images | Candidate | Key from api.data.gov; terms not checked |
| [Rijksmuseum](https://data.rijksmuseum.nl/) | Dutch art and objects | Candidate | Key and terms not checked; low relevance to Newbury |
| [US National Archives catalog](https://www.archives.gov/research/catalog) | US federal records | Candidate | Not checked |
| [Commonwealth War Graves Commission](https://www.cwgc.org/) | War dead and cemeteries | Candidate | No public API known; data access to check |
| [BillionGraves](https://billiongraves.com/) | Gravestone photos and transcriptions | Candidate | Partner API not checked |
| [Wolfram\|Alpha](https://products.wolframalpha.com/api) | Calculations: old money, units, dates, astronomy | Candidate | AppID key; free tier is 2,000 non-commercial calls a month, commercial licence needed. Most of this can be done locally |
| [UK Museum Data Service](https://museumdata.uk/) | UK museum collections, one search | Candidate | Public museum list open; object search needs a token |
| [Companies House](https://developer.company-information.service.gov.uk/) | Companies, officers, filings | Candidate, **handle with care** | Free key. Names and addresses of living directors: never a people search |
| [OpenCorporates](https://api.opencorporates.com/) | Companies worldwide | Candidate | Key; free tier is non-commercial (share-alike) |
| [Charity Commission register](https://api-portal.charitycommission.gov.uk/) | Charities, trustees, accounts | Candidate | Free key; living trustees |
| [FRED](https://fred.stlouisfed.org/docs/api/fred/) | Economic time series | Candidate | Free key; series have their own terms |
| [Open-Meteo Historical](https://open-meteo.com/en/docs/historical-weather-api) | Modelled weather worldwide since 1940 | Candidate | Free for non-commercial use; commercial plan needs a key. Modelled, not observed |
| [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/) | ERA5 reanalysis and climate data | Candidate | Account and key |
| [NOAA NCEI](https://www.ncei.noaa.gov/) | Historical weather observations | Candidate | Token |
| [NASA Earthdata](https://www.earthdata.nasa.gov/) | Satellite imagery and environment | Candidate | Login |
| [CEDA MIDAS-Open](https://catalogue.ceda.ac.uk/) | UK weather station observations | Candidate | Registration; OGL |
| [Delpher](https://www.delpher.nl/) (Netherlands) | Dutch newspapers and books | Candidate | API key on request |
| [Deutsche Digitale Bibliothek](https://www.deutsche-digitale-bibliothek.de/) | German libraries, archives, newspapers | Candidate | Free key |
| [Espacenet OPS](https://www.epo.org/en/searching-for-patents/data/web-services/ops) | Patents and inventors | Candidate | Key; usage quotas |
| [Semantic Scholar](https://www.semanticscholar.org/product/api) | Academic papers | Candidate | Works without a key at low rates; key on request |
| [Discogs](https://www.discogs.com/developers) | Recordings and releases | Candidate | Token; low relevance |
| [Human Mortality Database](https://www.mortality.org/) | Long-run mortality by country | Candidate | Registration; research use |
| [HM Land Registry business services](https://use-land-property-data.service.gov.uk/) | Ownership, leases, corporate owners | Candidate, **handle with care** | Account and key; some data paid |

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
| SunCalc | Sun and moon position for a place and time, in the browser (dating photos by shadows) | Candidate | BSD-2 (check) |
| Skyfield | Precise astronomy in Python | Candidate | MIT (check) |
| DuckDB | Exploring large downloaded datasets (CSV, Parquet) | Candidate | MIT |
| Plotly.js | Charts and timelines | Candidate | MIT |
| Apache Superset | Data dashboards (internal) | Candidate | Apache-2.0 |
| Grafana | Time-series dashboards | Candidate | AGPL: internal use only, never in our code |
| TanStack Table, TanStack Virtual | Very large tables in the Explorer | Planned | MIT |
| Gramps, webtrees, Omeka S, AtoM, Archivematica, Discourse and other GPL/AGPL projects | Design reference only | **Not used in the core** | GPL / AGPL |

## 10. Wider context: further afield

Sources that aren't family history but help describe the world people lived in, or are simply rich. **Context is not evidence:** a regional wage, a modelled temperature or a stranger's diary describes the period, never a particular ancestor. Unless marked, none of these terms have been checked. "Claude" in the From column means suggested in our own review rather than in the pasted lists.

### Property, planning and land

| Source | What it gives | Status | Notes |
|---|---|---|---|
| [HM Land Registry Price Paid](https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads) | Every house sale in England and Wales since 1995 | Candidate (checked) | OGL, but address data may only be displayed for property price information services; needs a legal check before building |
| [UK PlanIt](https://www.planit.org.uk/) | ~20 million planning applications, with an API | Candidate (checked) | No key; commercial use not addressed and planning documents are copyright. Ask first |
| [Planning Data England](https://www.planning.data.gov.uk/) | Conservation areas, listed buildings, constraints (100+ datasets) | Candidate | OGL API, no key; the service was down when tested (7 Nov 2026) |
| 1910 Valuation Office Survey ("Lloyd George's Domesday"), TNA IR 58 | A record of almost every property in 1910: owner, occupier, value | Partner / link out | From: Claude. Catalogued in TNA Discovery; maps at county record offices. Superb for "What was here?" |
| Tithe maps and apportionments (TNA IR 29/30) | Who owned and occupied each field c.1840 | Link out | From: Claude. Berkshire copies at the record office |
| Enclosure awards and maps | Land reallocation, 18th–19th centuries | Partner | From: Claude. Record office |
| [Valuation Office Agency](https://www.gov.uk/government/organisations/valuation-office-agency) | Council tax bands, business rates | Candidate | Modern only |
| [Coal Authority](https://www.gov.uk/government/organisations/the-coal-authority) | Mine plans and workings | Candidate | From: Claude. Not relevant to Newbury; keep for other regions |

### Money, prices, business and failure

| Source | What it gives | Status | Notes |
|---|---|---|---|
| [Bank of England: A millennium of macroeconomic data](https://www.bankofengland.co.uk/statistics/research-datasets) | Prices, wages, rates, some series from 1086 | Candidate | Downloads |
| Bank of England Bank Rate (from 1694) and the IADB | Interest and exchange rates | Candidate | From: Claude. Downloads |
| [TNA currency converter](https://www.nationalarchives.gov.uk/currency-converter/) | Old money to modern values, 1270–2017 | Link out | From: Claude. No API; explains what an old sum would buy |
| [MeasuringWorth](https://www.measuringworth.com/) | Historical wages, prices, values | Link out | Terms restrict reuse |
| [Nationwide house price index](https://www.nationwide.co.uk/house-price-index/) | UK house prices quarterly since 1952 | Candidate | From: Claude. Downloads; terms to check |
| [ONS](https://developer.ons.gov.uk/) and [NOMIS](https://www.nomisweb.co.uk/) | Census, population, employment, earnings | Candidate | ONS API is open with no key (OGL) |
| [Insolvency Service statistics](https://www.gov.uk/government/collections/insolvency-service-official-statistics) | Bankruptcy and company failure rates; some series from 1960 | Candidate | OGL downloads. Individual bankruptcies come from The Gazette (live) |
| [Jordà–Schularick–Taylor Macrohistory Database](https://www.macrohistory.net/) | Long-run credit, housing, banking | Candidate | Research licence to check |
| [Broadberry et al. British economic growth data](https://www.nuffield.ox.ac.uk/) | Output, productivity, wages | Link out | Research publications |
| [NBER Macrohistory](https://www.nber.org/research/data/nber-macrohistory-database) | Historical business data | Candidate | Mostly US |
| Fire insurance: Sun Fire Office and Royal Exchange registers (London Metropolitan Archives); Goad fire insurance plans (British Library) | Who insured which building and what it was used for, 1710s–1960s | Partner | From: Claude. Indexed in TNA Discovery; Goad plans show building materials and uses street by street |
| Lloyd's Register Heritage and Education Centre | Ship surveys, marine insurance | Link out | Ships and sailors |

### Weather, climate, sun and sky

| Source | What it gives | Status | Notes |
|---|---|---|---|
| [HadUK-Grid](https://www.metoffice.gov.uk/research/climate/maps-and-data/data/haduk-grid) | UK gridded temperature and rainfall, some from 1836 | Candidate | OGL downloads |
| Met Office historic station data | Long-running monthly records at selected stations | Candidate | Open downloads |
| Met Office Daily Weather Reports (Digital Archive) | Daily UK weather maps and observations from the 1860s | Candidate | From: Claude. Scans; "Weather Rescue" volunteers transcribed many |
| [Chronology of British Hydrological Events](https://www.cbhe.hydrology.org.uk/) | Floods, droughts and storms recorded over centuries | Candidate | From: Claude. Local events with sources |
| [Environment Agency data](https://environment.data.gov.uk/) | River levels, rainfall, recorded flood outlines, hydrology | Candidate | OGL, open APIs |
| [Hadley Centre observations](https://www.metoffice.gov.uk/hadobs/) | Central England Temperature from 1659 | Candidate | Downloads |
| [USGS earthquakes](https://earthquake.usgs.gov/fdsnws/event/1/) | Earthquakes worldwide | Candidate | Open API, public domain; rare in Britain |
| NASA eclipse catalogues | Past eclipses | Candidate | Public domain |
| SunCalc (see programs) | Where the sun was for a date, time and place | Program | Runs in the browser; for dating photos by their shadows |
| [NOAA solar calculator](https://gml.noaa.gov/grad/solcalc/) | Same, as a website | Link out | From: Claude |

### Museums, objects and art

| Source | What it gives | Status | Notes |
|---|---|---|---|
| The Met, Art Institute of Chicago | Objects and artworks | **Live** | See section 1 |
| [V&A Collections API](https://developers.vam.ac.uk/) | 1m+ records: clothing, textiles, household objects | Candidate | No key known; reuse is under V&A website terms section 9.3, which couldn't be read. Check, then build |
| [Science Museum Group](https://collection.sciencemuseumgroup.org.uk/) | Tools, machines, transport, medicine | Candidate | Not checked |
| [Smithsonian Open Access](https://www.si.edu/openaccess) | US museum objects | Key needed | See section 5 |
| [Rijksmuseum](https://data.rijksmuseum.nl/) | Dutch art and objects | Candidate | Not checked |
| [Museum of English Rural Life](https://merl.reading.ac.uk/), Reading | Farming, rural trades, Berkshire | Partner | Local; oral histories to check |
| [Portable Antiquities Scheme](https://finds.org.uk/) | Archaeological finds by the public, with locations | Candidate | Old sources suggest CC BY-SA and JSON output; no current terms found. Ask |
| [Open Domesday](https://opendomesday.org/) | Every place in Domesday Book (1086) | Candidate | Open API, no key; no licence stated. Ask |
| [Key to English Place-Names](https://kepn.nottingham.ac.uk/) | Origins of English place names | Link out | From: Claude |

### People's own words: oral history, diaries, testimony

These answer "what was it like?" in the words of people at the time. Rules: a few accounts can't speak for everyone ("people described…", not "everyone…"); someone else's memories describe the period, not your ancestor; most need permission to publish.

| Source | What it holds | Status | Notes |
|---|---|---|---|
| [Mass Observation](https://massobs.org.uk/) | 1937–1950s diaries, questionnaires and observations; since 1981, ~4,500 volunteers' writing | Partner | Held at The Keep, Brighton; digitised edition via Adam Matthew (licensed). Reuse terms not stated |
| [IWM Sound Archive](https://www.iwm.org.uk/collections) | 35,000+ recordings, 60,000+ hours, conflict since 1914 | Link out / partner | Licensing not shown |
| [BBC WW2 People's War](https://www.bbc.co.uk/history/ww2peopleswar/) | 47,000 memories and 14,000 photos | Link out | Reuse terms not found |
| [Burnett Archive of Working-Class Autobiographies](https://www.brunel.ac.uk/) | 349 autobiographies, c.1791–1945 | Partner | Brunel doesn't hold most copyrights |
| [Charles Booth's London](https://booth.lse.ac.uk/) | 1886–1903 notebooks and poverty maps | Candidate | Searchable; reuse not stated |
| [British Library: National Life Stories, Sounds](https://sounds.bl.uk/) | Life-story interviews across trades and places | Link out | Some services affected since the 2023 cyberattack |
| Millennium Memory Bank (BBC and British Library, 1998–99) | Thousands of interviews organised by region | Link out | Limited online access |
| UK Data Service qualitative archives (QualiBank) | Research interviews, e.g. "Family Life and Work Experience before 1918" (The Edwardians, 453 transcribed) and Young and Willmott's 1950s Bethnal Green study | Candidate | Registration; reuse per study |
| [Great Diary Project](https://www.thegreatdiaryproject.co.uk/) | 20,000+ unpublished diaries at Bishopsgate Institute | Partner | Reading room; privacy matters even for old diaries |
| Bishopsgate Institute oral histories | London work and community | Partner | |
| [London Museum](https://www.londonmuseum.org.uk/) oral histories | Docks, neighbourhoods; ~3,000 tapes, 500 videos | Partner | |
| [East Midlands Oral History Archive](https://www.le.ac.uk/emoha) | 4,000+ recordings, ~700 online | Candidate | Regional |
| Domesday Reloaded (BBC, 1986) | Local descriptions written by the public | Link out | |
| [Historypin](https://www.historypin.org/) | Photos and memories pinned to a map | Candidate | Not checked |
| [Europeana 1914–1918](https://www.europeana.eu/) | First World War letters and objects from families | Via Europeana | Part of the Europeana connector |
| Survey of English Dialects | Rural speech and working life recordings | Link out | British Library |
| London Lives (1690–1800) | 240,000 documents, 3.35m name references; relaunched Nov 2025 | Candidate | London only |
| Digital Panopticon (1780–1925) | Linked criminal lives | Candidate | Method worth studying for person matching |
| Reading Experience Database (1450–1945) | Evidence of reading in diaries and letters | Link out | |
| Observing the 1980s | Mass Observation and oral history | Link out | |
| Library of Congress Veterans History Project, StoryCorps | US testimony | Link out | Emigrants |
| Local oral history projects | Record offices, museums, societies | Partner | ArchiveHub could help publish them |
| **ArchiveHub's own interviews** | A public memory bank, opt-in, separate consent, withdrawable | Idea | Needs a spec decision |

### Law, government and institutions

| Source | What it gives | Status | Notes |
|---|---|---|---|
| [legislation.gov.uk](https://www.legislation.gov.uk/developer) | Acts and how they changed, e.g. Poor Law Acts | Candidate | OGL API, no key; returns XML/Atom, so needs an XML reader in the connector |
| [Find Case Law](https://caselaw.nationalarchives.gov.uk/) | Court judgments | Candidate | Open Justice Licence restricts computational analysis without a licence |
| [BAILII](https://www.bailii.org/) | Court judgments | Link out | No reuse |
| [Electoral Commission data](https://search.electoralcommission.org.uk/) | Donations, parties | Link out, **handle with care** | Living people |
| [Police.uk](https://data.police.uk/) | Street-level crime since 2010 | Not for us | Modern and about living communities; no clear history use |
| Historic Hospital Admission Records Project | Children's hospital admissions 1852–1921 | Link out | From: Claude |
| [Find a will](https://probatesearch.service.gov.uk/) | Probate calendar from 1858 | Link out | From: Claude. No API |

### Transport, work and industry

| Source | What it gives | Status | Notes |
|---|---|---|---|
| Railway staff records (TNA RAIL series), [National Railway Museum](https://www.railwaymuseum.org.uk/) | Railway workers, many families | Link out | Catalogued in TNA Discovery |
| [Rail Map Online](https://www.railmaponline.com/) | Former railway routes | Link out | |
| Crew list projects (CLIP), Lloyd's Register | Ships and sailors | Link out | |
| [ShipIndex](https://www.shipindex.org/), [Wrecksite](https://www.wrecksite.eu/) | Ships in publications, wrecks | Link out | Terms to check |
| Trade union archives (Modern Records Centre, Warwick) | Working lives and disputes | Partner | |
| Espacenet, Google Patents | Inventors and inventions | Key / link out | See section 5 |
| [TfL Open Data](https://tfl.gov.uk/info-for/open-data-users/) | London transport today | Candidate | Modern |

### Nature, land and the sky above

| Source | What it gives | Status | Notes |
|---|---|---|---|
| [GBIF](https://www.gbif.org/developer/summary) | Species records by place, some centuries old | Candidate | Open API, no key; licences per dataset (CC0, CC BY, CC BY-NC) |
| [NBN Atlas](https://nbnatlas.org/) | British wildlife records | Candidate | Licences per record, some non-commercial |
| [British Geological Survey](https://www.bgs.ac.uk/) | Geology, boreholes, mines, quarries | Candidate | OGL for much; some licensed |
| Natural England, NatureScot, Forest Research | Designated sites, habitats, woodland | Candidate | OGL mostly |
| Landsat, Copernicus Sentinel | Land change since the 1970s | Candidate | Free; heavy data |

### Books, language, broadcasting and the web

| Source | What it gives | Status | Notes |
|---|---|---|---|
| [Wayback Machine](https://archive.org/help/wayback_api.php) | Old versions of websites | Candidate | Open availability API; useful for moving historians' old sites (WP7) |
| [Open Library](https://openlibrary.org/developers/api) | Book editions and authors | Partner (checked) | API "not intended for high-traffic commercial infrastructure": ask openlibrary@archive.org; monthly dumps exist |
| [Google Books API](https://developers.google.com/books) | Book search, some previews | Candidate | Key optional; terms to check |
| [Gallica](https://gallica.bnf.fr/) (France) | French newspapers and books | Candidate | Non-commercial reuse free; commercial reuse licensed |
| Oxford DNB, Oxford English Dictionary | Biographies, historical word meanings | Link out | Subscription |
| Google Books Ngram Viewer | How often words were printed, by year | Link out | |
| [BBC Programme Index](https://genome.ch.bbc.co.uk/) | Every BBC radio and TV listing since 1923 | Link out | No API |
| [MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_API) | Recordings and artists | Candidate | Open API; core data CC0 |
| IMDb datasets | Films and people | Not allowed | Non-commercial only |
| [Pleiades](https://pleiades.stoa.org/), [Getty vocabularies](https://www.getty.edu/research/tools/vocabularies/) | Ancient places; places, artists and art terms | Candidate | Pleiades CC BY; Getty ODC-By |
| [Who's On First](https://whosonfirst.org/) | Place records | Candidate | Licences per source |
| [GDELT](https://www.gdeltproject.org/) | Global news events since 1979 | Candidate | Fits the OSINT tools better |
| [Zooniverse](https://www.zooniverse.org/) projects | Volunteer transcriptions (weather logs, ships, letters) | Candidate | From: Claude. Data per project |

### Handle with care, or not at all

- **DNA services:** genetic data is highly sensitive. Not before specialist advice.
- **Living-people datasets** (Companies House, electoral data, Land Registry ownership, recent Gazette notices, police data): useful for businesses and buildings, but they can be used to find someone. No "people search", and the same living-people rules as everywhere else.

## 11. Records by life event: where the originals are

Commercial sites mostly license, digitise and index records held by archives, and those licences are usually non-exclusive. So for each kind of record we note who holds the original, whether there's a free or independent route, and what it costs. This table is the start of a "where to find this record" guide for users. Items marked **Checked** were confirmed on 7 Nov 2026; the rest are leads.

| Life event | Where the originals or indexes are | Free or independent route | Cost and notes |
|---|---|---|---|
| Births and deaths, England and Wales | General Register Office (GRO) | **Checked:** free historical index online: births over 100 years old, deaths 1837–1957 | Online View image about £3, PDF about £8 (check current fees); needs the GRO index reference; images aren't certified copies. No API; link and guide |
| Births, marriages, deaths (indexes) | GRO; FreeBMD (volunteers) | FreeBMD free search | **Checked:** Free UK Genealogy invites bulk-data enquiries for research with clear public benefit (terms not published) |
| Baptisms, marriages, burials (parish registers) | County record offices (Royal Berkshire Archives for us); FreeREG transcriptions | FreeREG free search | Record office licences to commercial sites are often non-exclusive: ask about ours |
| Census 1841–1921 | The National Archives; FreeCEN (partial); I-CeM (research microdata, 1851–1911) | FreeCEN free search; 1921 free to view at Kew, Manchester and the National Library of Wales | I-CeM names and addresses need a special licence; the statistical version could feed context |
| Military service | The National Archives (MOD records transferring, about 10m); CWGC; regimental museums; IWM; RAF Museum; National Museum of the Royal Navy; National Army Museum | Discovery catalogue (connector built) | **Checked:** TNA charges for MOD service record searches and copies from 2 Feb 2026; Ancestry is digitising about a third, publishing people born over 100 years ago in tranches. Never imply someone fought in a battle because their unit did |
| School and university | Schools, county record offices, university archives; Archives Hub (350+ institutions) | Archives Hub has SRU and OAI-PMH interfaces | Reuse terms for Hub descriptions not found: ask Jisc. Cambridge Alumni Database (c.1200–1900) is experimental; reuse questions go to the university |
| Work and occupations | Trade directories; occupational censuses; CAMPOP (Cambridge) | Leicester directories; Internet Archive | CAMPOP datasets "used by researchers worldwide"; access terms on request |
| Business and bankruptcy | The Gazette (live), Companies House, trade directories | The Gazette connector | |
| Residence, land and houses | Census, electoral registers, directories, tithe maps (c.1840), 1910 Valuation Office Survey, deeds | Record offices | Electoral registers name living people: handle with care |
| Taxation | Hearth tax, land tax, valuation rolls | Record offices, TNA | |
| Poverty and welfare | Poor Law union records, workhouse registers, settlement examinations | Record offices; explanations now in the glossary | |
| Crime, courts, prisons | Quarter sessions, assizes, prison registers, coroners' inquests, police gazettes; Old Bailey, Digital Panopticon | Old Bailey Online, Digital Panopticon | |
| Immigration and emigration | Passenger lists, naturalisation (TNA) | Trove, DigitalNZ, DPLA connectors built | |
| Probate | Probate calendar from 1858 | gov.uk probate search (no API) | |
| Religion | Parish, chapel and nonconformist registers (TNA RG 4 etc.) | | |
| Scotland | ScotlandsPeople / National Records of Scotland (statutory registers from 1855, also wills, valuations, prison registers) | | Paid images; privacy cut-offs for online images (reported as 100 years births, 75 marriages, 50 deaths: check) |
| Ireland and Northern Ireland | IrishGenealogy.ie; GRONI | IrishGenealogy.ie free search | GRONI paid |

**Directory of government APIs:** the [UK Government API Catalogue](https://www.api.gov.uk/) lists APIs from public bodies; being listed doesn't mean public or commercial access.

### Sport

| Source | What it gives | Status | Notes |
|---|---|---|---|
| [engsoccerdata](https://github.com/jalapic/engsoccerdata) | English league results 1888 onwards, FA Cup from 1871 | Candidate | A listing says non-commercial use with citation; check the repo's licence |
| [Sean Elvidge's England results](https://seanelvidge.com/blog/2024/All_England_football_league_results) | Top four divisions, updated often | Candidate | Builds on engsoccerdata; licence not found |
| [schochastics/football-data](https://github.com/schochastics/football-data) | 1.2m results, 207 leagues, 1888–2023 (Parquet) | Candidate | Licence not stated |
| OpenFootball | Fixtures and results | Candidate | Licence to check |
| StatsBomb Open Data | Modern match events | Not for us | Modern, research terms |
| Cricsheet | Ball-by-ball cricket data | Candidate | Licence to check |
| ESPNcricinfo, Olympedia | Scorecards, Olympians | Link out | No bulk reuse |
| MCC Collections, World Rugby Museum, club archives | Objects, photos, records | Partner | |
| Local newspapers | Match reports naming local players | Partner | The richest source for Newbury clubs |

### Genealogy software and services

| Name | Note |
|---|---|
| Gramps Web / Gramps Web API | Suggested as the engine; we keep it as a design reference because it's AGPL (ADR-010). Our own importer already reads GEDCOM 5.5.1 and 7 lines; GedZip (media bundled) is a later addition |
| GEDCOM 7 and GedZip | FamilySearch specification; GedZip packages media with the tree |
| MyHeritage, TheGenealogist | Commercial; users can import their own GEDCOM exports |

---

## 12. From Update 1 and Addendum v3 (10 Nov 2026)

New sources and repos from the two update documents in [updates/](updates/). Sources already listed above aren't repeated. Terms are as the documents report them unless marked as checked by us; treat them as leads until a terms page is read. Each data source is also in the in-app source directory, so the assistant can point to it.

### Art and images

| Source | What it gives | Terms (as reported) | Plan |
|---|---|---|---|
| [Yale Center for British Art](https://britishart.yale.edu/terms) | British art, including landscapes and rural scenes. | Update 1 reports: public domain images can be used without permission or fees; commercial use isn't addressed on that page. Check before showing in a paid product. | Culture items for the Life Report (WP14). First art source to connect. |
| [Cleveland Museum of Art Open Access](https://www.clevelandart.org/open-access-api) | 64,000+ artwork records and 37,000+ images, with an API (openaccess-api.clevelandart.org) and GitHub downloads. | Update 1 reports: CC0, commercial use allowed. Check each item's open-access flag. | Culture items for the Life Report (WP14). First art source to connect. |
| [Getty Open Content](https://www.getty.edu/about/whatwedo/opencontent.html) | 160,000+ images, including paintings, prints, maps and 19th-century photographs. | Update 1 reports: CC0 images, commercial use allowed. | Culture items for the Life Report (WP14). First art source to connect. |
| [British Library illustrations on Flickr Commons](https://www.libraryjournal.com/story/british-library-adds-1-million-public-domain-images-taken-from-17th-18th-and-19th-century-books-to-flickr-commons) | About 1 million illustrations from 17th–19th century books. | Update 1 reports: public domain. Captions are thin, so items need tagging before matching. | Illustrations for the Life Report once tagged (WP14). |
| [National Gallery (London)](https://www.nationalgallery.org.uk/paintings) | Western European paintings, c.1250–1900. | Update 1 reports: data CC0 and texts CC BY, but images non-commercial only. Use data and link to images. | Data only; link out for images. |
| [Tate collection](https://www.tate.org.uk/art) | British and modern art. A metadata snapshot is on GitHub (tategallery/collection). | Update 1 reports: metadata CC0, image reuse not covered. The GitHub data is an old snapshot. | Data only; link out for images. |
| [MoMA collection data](https://github.com/MuseumofModernArt/collection) | Modern artwork and artist metadata. | Metadata only; image rights are separate. | Low priority: mostly 20th century. |
| [Art UK](https://artuk.org/) | Paintings and sculpture in UK public collections, many tied to places. | Update 1 reports: permissions vary by artwork; no API mentioned (see artuk.org/about/image-use). | Link out; ask about a partnership for local artworks. |
| [Government Art Collection](https://artcollection.culture.gov.uk/) | Art owned by the UK government, including topographical views. | Update 1 reports: a paid licence is needed for reproduction. | Link out. |
| [Ashmolean Museum collections](https://www.ashmolean.org/collections) | Art and objects, including Oxford views. | Not checked. | Link out; check terms. |
| [British Museum collection](https://www.britishmuseum.org/collection) | Prints, drawings and objects, including satirical prints and topographical views. | Not checked. | Link out; check terms. |
| [National Galleries of Scotland](https://www.nationalgalleries.org/) | Scottish art and portraits. | Not checked. | Link out; check terms. |
| [London Picture Archive](https://www.londonpicturearchive.org.uk/) | Historical images of London streets and buildings. | Not checked. | Link out; check terms. |
| [National Gallery of Art (US) open access](https://www.nga.gov/open-access-policy) | Open images and artwork data where marked. | Addendum v3 reports open images where indicated; not checked. | Later art source. |
| [Digital Bodleian](https://digital.bodleian.ox.ac.uk/) | Digitised books, manuscripts, prints, ballads and maps, with IIIF. | Not checked. | Link out; IIIF viewing later. |
| [Iconclass](https://github.com/iconclass/data) | Subject codes for what artworks show (harvest, market, soldier...). | Update 1 reports: CC0. | Subject tagging for culture items, linked to HISCO job codes (WP14). |

### Literature and poetry

| Source | What it gives | Terms (as reported) | Plan |
|---|---|---|---|
| [Wikisource](https://en.wikisource.org/) | Proofread transcriptions of public domain texts. | Not checked; licence varies by page. | Public domain passages for the Life Report. |
| [Standard Ebooks](https://standardebooks.org/) | Carefully produced editions of public domain books (sources on GitHub). | Check each edition's rights. | Clean public domain texts. |
| [Poetry Archive](https://poetryarchive.org/) | 10,369 poems, many read by the poets. | Update 1 reports: free to listen to; reuse terms not stated. | Link out. |
| [Poetry Foundation](https://www.poetryfoundation.org/) | Poems and poet biographies. | Addendum v3: metadata and discovery only; don't bulk copy poems. | Link out. |
| [Oxford English Dictionary](https://www.oed.com/) | Historical meanings of words, with dated quotations. | Subscription and licensing needed. | Link out; licence later for Explain this record. |
| [Hardy's Wessex (fictional places)](https://en.wikipedia.org/wiki/Thomas_Hardy%27s_Wessex) | Hardy's fictional names for real places. | Update 1 reports: in Jude the Obscure 'Kennetbridge' is Newbury (or possibly Hungerford), 'Alfredston' Wantage, 'Aldbrickham' Reading and 'Christminster' Oxford. Secondary source; check against a Hardy scholar before storing. | Seed for FictionalPlace links (WP14) once checked. |
| [A Literary Atlas of Wales](https://www.swansea.ac.uk/arts-and-humanities/arts-and-humanities-research/our-recent-research-projects/a-new-literary-geography/) | Twelve novels mapped to real places. | Update 1 reports: a design model; data terms unclear. | Design reference for literary maps. |

### Ballads, folk songs, rhymes and folklore

| Source | What it gives | Terms (as reported) | Plan |
|---|---|---|---|
| [Vaughan Williams Memorial Library](https://www.vwml.org/) | Folk songs, the Roud indexes and the Full English archive. | Update 1 reports: permission needed beyond private study (VWML licensing page). | Ask for permission to link and quote (WP14). |
| [Roud Folk Song Index](https://en.wikipedia.org/wiki/Roud_Folk_Song_Index) | Index of English-language folk songs and their variants. | Update 1 reports: its own pages weren't reachable; hosted by the VWML. | Via the VWML. |
| [Traditional Ballad Index](https://balladindex.org/) | Scholarly index of ballads and folk songs. | Not checked; check reuse of downloadable data. | Link out. |
| [Bodleian broadside ballads](https://www.bodleian.ox.ac.uk/collections-and-resources/special-collections/finding-aids-and-catalogues/ballads) | Nearly 30,000 printed ballads with woodcuts, 16th–20th century. | Update 1 reports: now in SOLO, images planned for the end of 2026; reuse terms not stated. | Ask for permission (WP14). |
| [English Broadside Ballad Archive](https://en.wikipedia.com/wiki/English_Broadside_Ballad_Archive) | Early modern ballads and woodcuts. | Update 1 reports: terms not checked. | Link out. |
| [Child Ballads (online transcription)](https://peterrobins.co.uk/ballads/) | Francis James Child's 305 ballads with 1,216 variants, published 1882–1898. | Update 1 reports: the original is old enough to be public domain, but this site's transcriptions don't state terms. Prefer a public domain scan. | Public domain ballad texts (WP14). |
| [Halliwell: The Nursery Rhymes of England](https://www.gutenberg.org/ebooks/32415) | J. O. Halliwell-Phillipps' Victorian collection of nursery rhymes. | Title confirmed on Project Gutenberg 10 Nov 2026. Follow Gutenberg's trademark and licence rules. | Public domain rhymes for the Life Report (WP14). |
| [Halliwell: Popular Rhymes and Nursery Tales](https://www.gutenberg.org/ebooks/35707) | J. O. Halliwell-Phillipps' collection of popular rhymes and tales. | Title confirmed on Project Gutenberg 10 Nov 2026. | Public domain rhymes and tales (WP14). |
| [Oxfordshire folklore notes (Bodleian)](https://archives.bodleian.ox.ac.uk/repositories/2/archival_objects/38363) | Early 20th-century folklore notes catalogued by village. | Update 1 reports: archive material. | Link out. |
| [Folklore Society county surveys](https://england.prm.ox.ac.uk/englishness-Folklore-surveys.html) | History of the county folklore surveys begun in 1893. | Update 1 reports: Berkshire wasn't in the 1897 allocation. | Reference for which counties have surveys. |
| [The Folklore Society](https://folklore-society.com/) | Folklore literature, customs and children's lore. | Not checked. | Possible partner for checked folklore explanations. |
| [English Folk Dance and Song Society](https://www.efdss.org/) | Home of the VWML and the Full English digital archive. | Not checked. | With the VWML. |
| [Tobar an Dualchais](https://www.tobarandualchais.co.uk/) | Scottish traditional song, story and oral testimony recordings. | Not checked. | Link out; ask about a partnership. |
| [Irish Traditional Music Archive](https://www.itma.ie/) | Irish traditional music recordings, songs and manuscripts. | Not checked. | Link out; ask about a partnership. |

### Film

| Source | What it gives | Terms (as reported) | Plan |
|---|---|---|---|
| [BFI StoryTrails](https://player.bfi.org.uk/free/collection/storytrails-the-peoples-map) | Free films linking local stories and archive footage to 15 towns and cities. | Update 1 reports: free to watch; the wider Britain on Film archive still needs checking. | Link out from places. |

### People, schools and statistics

| Source | What it gives | Terms (as reported) | Plan |
|---|---|---|---|
| [Cambridge Alumni Database (ACAD)](https://venn.lib.cam.ac.uk/) | Members of Cambridge University, about 1200–1900. | Update 1 reports: experimental; ask about reuse. | Where to look: university education. |
| [Get Information About Schools](https://get-information-schools.service.gov.uk/) | Register of schools in England, including closed ones. | Not checked; assess the download. | Historic school identifiers for education records. |
| [HESA](https://www.hesa.ac.uk/) | Higher education statistics. | Not checked. | Context only. |
| [Our World in Data](https://ourworldindata.org/) | Long-run statistics on health, population and living standards. | Not checked. | Life and times context, labelled as population figures (WP12). |
| [Gapminder data](https://www.gapminder.org/data/) | Long-run indicators for countries. | Not checked. | Life and times context (WP12). |

### Research, newspapers and sound

| Source | What it gives | Terms (as reported) | Plan |
|---|---|---|---|
| [British Library Sounds](https://sounds.bl.uk/) | Recorded sound, oral history and dialect recordings. | Named as a testimony lead in Update 1 reports; not checked. | Link out. |
| [Fitzwilliam Museum](https://fitzmuseum.cam.ac.uk/) | Art and objects. | Named as a lead in Update 1 reports; not checked. | Link out; check terms. |
| [Chronicling America](https://chroniclingamerica.loc.gov/) | Digitised US newspapers. | The Library of Congress API blocked our server with a bot challenge earlier; ask for access. | US newspapers for emigrant families. |
| [Crossref](https://www.crossref.org/) | Metadata for scholarly articles and books. | Named as a lead in Update 1 reports; not checked. | Research papers as context, alongside OpenAlex. |
| [arXiv](https://arxiv.org/) | Preprints, including history of science. | Named as a lead in Update 1 reports; not checked. | Low priority. |
| [PubMed](https://pubmed.ncbi.nlm.nih.gov/) | Medical literature, including history of medicine and disease. | Named as a lead in Update 1 reports; not checked. | Context for historical causes of death; never a claim about a person. |

### Bringing trees home from other sites

| Site | Export route | What's missing (as reported) |
|---|---|---|
| [Ancestry](https://help-redir.ancestry.com/hc/en-ca/articles/53933352542867-Uploading-and-Downloading-Trees) | The tree owner downloads a GEDCOM | Photos and media; outside services are blocked from downloading them |
| [MyHeritage](https://www.myheritage.com/help/en/articles/12851866-how-do-i-download-export-a-gedcom-file-of-my-family-tree-from-my-family-site) | GEDCOM export from Manage Trees | Photo files ([help](https://www.myheritage.com/help/en/articles/12851303-do-my-photos-transfer-with-a-gedcom-file)), though links can be included |
| [Findmypast](https://www.myheritage.com/help/en/articles/12851478-how-can-i-export-a-gedcom-of-my-family-tree-from-findmypast) | GEDCOM export from the tree page | Contents not documented |
| [FamilySearch](https://familysearch.org/innovate/export) | Through listed apps only, up to eight generations, GEDCOM 7 | Photos, and spouses other than the preferred one |

### Code to learn from

Licences checked on GitHub on 10 November 2026 (API or repo page). The rule from Update 1 applies: don't reuse code with no licence or a non-commercial one, and only study GPL and AGPL code. "Licence file (type not recognised)" means GitHub couldn't classify it: read it before any use.

| Repo | What's useful | Licence | Decision | Shapes |
|---|---|---|---|---|
| [gmarcon/webtrees-time-travel-map](https://github.com/gmarcon/webtrees-time-travel-map) | Timeline slider, alive-count chart and autoplay. | GPL-3.0 | Study only; don't copy code | Lifeline (WP9) |
| [connorkeetch/kinwhere](https://github.com/connorkeetch/kinwhere) | GEDCOM to ancestry map, migration view and research hints. | MIT | May reuse with credit, after review | Lifeline (WP9) |
| [oh-kay-blanket/family-plot](https://github.com/oh-kay-blanket/family-plot) | 3D tree positioned by birth year, with photos. | GPL-3.0 | Study only; don't copy code | Lifeline (WP9) |
| [n1kozor/Tree-Monk](https://github.com/n1kozor/Tree-Monk) | Investigation board, historic maps and timelines. Update 1 reports a non-commercial licence. | Licence file (type not recognised) | Ideas only: non-commercial | Brick-wall board (later) |
| [donatso/family-chart](https://github.com/donatso/family-chart) | Editable tree built on D3. | MIT | May reuse with credit, after review | Tree tools (WP10) |
| [ErikGartner/dTree](https://github.com/ErikGartner/dTree) | Trees with multiple parents, built on D3. | MIT | May reuse with credit, after review | Tree tools (WP10) |
| [BenPortner/js_family_tree](https://github.com/BenPortner/js_family_tree) | Interactive tree using d3-dag. | GPL-3.0 | Study only; don't copy code | Tree tools (WP10) |
| [nliautaud/gedcom-svg-fanchart](https://github.com/nliautaud/gedcom-svg-fanchart) | Fan charts from GEDCOM. | MIT | May reuse with credit, after review | Tree tools (WP10) |
| [davorg-cpan/svg-timeline-genealogy](https://github.com/davorg-cpan/svg-timeline-genealogy) | Genealogy timelines in SVG. | None found | Read the licence file first | Lifeline (WP9) |
| [michelesalvador/GedcomGraph](https://github.com/michelesalvador/GedcomGraph) | Tree layouts on top of GEDCOM. | GPL-3.0 | Study only; don't copy code | Tree tools (WP10) |
| [dedovskaya/Tam-VR](https://github.com/dedovskaya/Tam-VR) | Exploring a tree in virtual reality. | None found | Read the licence file first | Ideas only |
| [picnicprojects/fanchart3d](https://github.com/picnicprojects/fanchart3d) | A GEDCOM fan chart as a 3D object. | None found | Read the licence file first | Ideas only |
| [DenisSergeevitch/ex-ussr-kinship-research](https://github.com/DenisSergeevitch/ex-ussr-kinship-research) | Evidence grades, places as they were at the time, name variants. | MIT | May reuse with credit, after review | Evidence model; places through time |
| [mattprusak/autoresearch-genealogy](https://github.com/mattprusak/autoresearch-genealogy) | Research prompts and templates. | MIT | May reuse with credit, after review | Assistant prompts |
| [igormel81/genealogy-mcp](https://github.com/igormel81/genealogy-mcp) | MCP server knowing 171 archives, with links and plans. | MIT | May reuse with credit, after review | Where to look; source directory |
| [mjsmulligan/irish-genealogy-research](https://github.com/mjsmulligan/irish-genealogy-research) | Record-linkage scores, household-based matching. | Licence file (type not recognised) | Read the licence file first | Merge suggestions (WP10) |
| [DigitalArchivst/Open-Genealogy](https://github.com/DigitalArchivst/Open-Genealogy) | Prompts based on the genealogical proof standard. | Custom (not recognised) | Read the licence file first | Ideas only |
| [cabout-me/gramps-mcp](https://github.com/cabout-me/gramps-mcp) | AI assistant tools for a Gramps tree. | AGPL-3.0 | Study only; don't copy code | Ideas only |
| [elboletaire/family-tree-kit](https://github.com/elboletaire/family-tree-kit) | Agent-built trees where every fact needs a document. | MIT | May reuse with credit, after review | Evidence rules |
| [Kinprove/genealogy-research-recipes](https://github.com/Kinprove/genealogy-research-recipes) | Research recipes for DNA and record searches. | Custom (not recognised) | Read the licence file first | Ideas only |
| [ACiDekCZ/strom-research](https://github.com/ACiDekCZ/strom-research) | AI parish register research. | AGPL-3.0 | Study only; don't copy code | Ideas only |
| [sodejm/AncestryLLM](https://github.com/sodejm/AncestryLLM) | Local tools for GEDCOM and RootsMagic. | MIT | May reuse with credit, after review | Imports (WP10) |
| [bartfeenstra/betty](https://github.com/bartfeenstra/betty) | Encyclopedia-style family history websites. | GPL-3.0 | Study only; don't copy code | Home / publishing |
| [tymrtn/family-book](https://github.com/tymrtn/family-book) | Private, self-hosted family tree and archive. | MIT | May reuse with credit, after review | Ideas |
| [adityaimamz/WarisanAI](https://github.com/adityaimamz/WarisanAI) | Family archive with stories, photos and timelines. | MIT | May reuse with credit, after review | Life Story (WP11) |
| [linyuanguo/Yugraphy](https://github.com/linyuanguo/Yugraphy) | AI that reads printed family books. | Licence file (type not recognised) | Read the licence file first | Ideas only |
| [yojowa/familylore-plugin](https://github.com/yojowa/familylore-plugin) | Reads handwritten family letters. | MIT | May reuse with credit, after review | Handwriting |
| [Scheldt-LLC/genealogy_ai](https://github.com/Scheldt-LLC/genealogy_ai) | Extracts details from documents with OCR and AI. | MIT | May reuse with credit, after review | Document reading |
| [dekochka/genea-metric-books-transcriber-scripts](https://github.com/dekochka/genea-metric-books-transcriber-scripts) | Transcribes handwritten register images. | Custom (not recognised) | Read the licence file first | Ideas only |
| [jon-mqn/genealogical_record_linkage](https://github.com/jon-mqn/genealogical_record_linkage) | Machine learning for matching records. | Unlicense | May reuse with credit, after review | Merge suggestions (WP10) |
| [SultanOrazbayev/awesome-usa-census-linkage](https://github.com/SultanOrazbayev/awesome-usa-census-linkage) | List of census linkage projects. | None found | Read the licence file first | Reading list |
| [mumuy/relationship](https://github.com/mumuy/relationship) | The correct term for any relative (Chinese kinship). | MIT | May reuse with credit, after review | Relationship naming |
| [jammyfu/xiangsheng-genealogy](https://github.com/jammyfu/xiangsheng-genealogy) | Master-to-apprentice performance lineages. | MIT | May reuse with credit, after review | Lineages (WP13) |
| [spear34000/Gwageo_Explorer](https://github.com/spear34000/Gwageo_Explorer) | 84,525 people who passed Korean civil service exams. | MIT | May reuse with credit, after review | Lineages (WP13) |
| [awesomelena/european-dynasties](https://github.com/awesomelena/european-dynasties) | Royal and noble marriages. | MIT | May reuse with credit, after review | Lineages (WP13) |
| [lmallez/wikidata-tree-generator](https://github.com/lmallez/wikidata-tree-generator) | Trees of historical figures from Wikidata. | MIT | May reuse with credit, after review | Lineages (WP13) |
| [samwilson/wabmd](https://github.com/samwilson/wabmd) | Matching an official index to Wikidata. | None found | Read the licence file first | Ideas only |
| [crouffer/obsidian-bible-vault](https://github.com/crouffer/obsidian-bible-vault) | 4,427 linked people and places. | MIT | May reuse with credit, after review | Ideas |
| [metmuseum/openaccess](https://github.com/metmuseum/openaccess) | Met artwork metadata (CSV). | CC0-1.0 | Data reusable (CC0) | Culture items (WP14) |
| [ClevelandMuseumArt/openaccess](https://github.com/ClevelandMuseumArt/openaccess) | Cleveland artwork metadata and eligible images. | CC0-1.0 | Data reusable (CC0) | Culture items (WP14) |
| [tategallery/collection](https://github.com/tategallery/collection) | Tate artwork metadata snapshot. | CC0-1.0 | Data reusable (CC0) | Culture items (WP14) |
| [MuseumofModernArt/collection](https://github.com/MuseumofModernArt/collection) | MoMA artwork metadata. | CC0-1.0 | Data reusable (CC0) | Culture items (WP14) |
| [art-institute-of-chicago/api-data](https://github.com/art-institute-of-chicago/api-data) | Art Institute of Chicago data dump. | None found | Read the licence file first | Culture items (WP14) |
| [georgeblck/art-datasets](https://github.com/georgeblck/art-datasets) | Directory of art datasets. | None found | Read the licence file first | Reading list |
| [iconclass/data](https://github.com/iconclass/data) | Iconclass subject codes. | CC0-1.0 | Data reusable (CC0) | Culture items (WP14) |
| [GLAM-Workbench/digitalnz](https://github.com/GLAM-Workbench/digitalnz) | DigitalNZ notebooks. | MIT | May reuse with credit, after review | Connector examples |
| [GLAM-Workbench/trove-newspapers](https://github.com/GLAM-Workbench/trove-newspapers) | Trove newspaper notebooks. | MIT | May reuse with credit, after review | Connector examples |
| [GLAM-Workbench/trove-newspaper-harvester](https://github.com/GLAM-Workbench/trove-newspaper-harvester) | Trove newspaper harvester. | MIT | May reuse with credit, after review | Connector examples |
| [booknlp/booknlp](https://github.com/booknlp/booknlp) | Characters, quotations and places in novels. | MIT | May reuse with credit, after review | Literature (WP14) |
| [cltk/cltk](https://github.com/cltk/cltk) | Pre-modern language pipelines. | MIT | May reuse with credit, after review | Later |
| [stanfordnlp/stanza](https://github.com/stanfordnlp/stanza) | Named entities and sentence analysis. | Licence file (type not recognised) | Read the licence file first | Document reading |
| [standardebooks/tools](https://github.com/standardebooks/tools) | EPUB production and validation. | Licence file (type not recognised) | Read the licence file first | Report export |
| [garethbjohnson/gutendex](https://github.com/garethbjohnson/gutendex) | Self-hostable Project Gutenberg catalogue API. | MIT | May reuse with credit, after review | Literature (WP14) |
| [cuthbertLab/music21](https://github.com/cuthbertLab/music21) | Analysing tunes and variants. | BSD-3-Clause | May reuse with credit, after review | Folk songs (later) |
| [humdrum-tools/humdrum-data](https://github.com/humdrum-tools/humdrum-data) | Structured music corpora. | None found | Read the licence file first | Folk songs (later) |
| [humdrum-tools/verovio-humdrum-viewer](https://github.com/humdrum-tools/verovio-humdrum-viewer) | Score rendering. | None found | Read the licence file first | Folk songs (later) |
| [humdrum-tools/humdrum-documentation](https://github.com/humdrum-tools/humdrum-documentation) | Music format documentation. | None found | Read the licence file first | Reading list |
| [docuracy/Locolligo](https://github.com/docuracy/Locolligo) | Geolocating heritage collection metadata. | Custom (not recognised) | Read the licence file first | Places |
| [inception-project/inception](https://github.com/inception-project/inception) | Human-assisted text annotation. Now at eclipse-inception/inception. | Apache-2.0 | May reuse with credit, after review | Later |
| [annotorious/annotorious](https://github.com/annotorious/annotorious) | Annotate people, objects and buildings on images. | BSD-3-Clause | May reuse with credit, after review | Galleries (WP11) |
| [dpla/dpla-frontend](https://github.com/dpla/dpla-frontend) | Federated search interface. | MIT | May reuse with credit, after review | Design reference |
| [wikimedia/mediawiki](https://github.com/wikimedia/mediawiki) | Wikisource platform. | Licence file (type not recognised) | Read the licence file first | Use the API instead |
| [quarto-dev/quarto-cli](https://github.com/quarto-dev/quarto-cli) | HTML, PDF and Word output. | MIT | May reuse with credit, after review | Life Report export (WP14) |
| [jgm/pandoc](https://github.com/jgm/pandoc) | Document conversion. | GPL-2.0 | Study only; don't copy code | Life Report export (WP14) |
| [typst/typst](https://github.com/typst/typst) | Print-quality typesetting. | Apache-2.0 | May reuse with credit, after review | Life Report export (WP14) |
| [citation-js/citation-js](https://github.com/citation-js/citation-js) | Citation formatting. | MIT | May reuse with credit, after review | Life Report bibliography (WP14) |
| [zotero/translation-server](https://github.com/zotero/translation-server) | Bibliographic metadata from web pages. | Licence file (type not recognised) | Read the licence file first | Saving finds |
| [Allmaps/Allmaps](https://github.com/Allmaps/Allmaps) | Georeferencing IIIF map images. | None found | Read the licence file first | Time map |
| [geneweb/geneweb](https://github.com/geneweb/geneweb) | Large genealogy trees. | GPL-2.0 | Study only; don't copy code | Comparison |
| [gramps-project/gramps](https://github.com/gramps-project/gramps) | Genealogy desktop data model. | GPL-2.0 | Study only; don't copy code | Import/export target |
| [gramps-project/gramps-web](https://github.com/gramps-project/gramps-web) | Genealogy web UI. | AGPL-3.0 | Study only; don't copy code | Comparison |
| [gramps-project/gramps-web-api](https://github.com/gramps-project/gramps-web-api) | Genealogy backend. | AGPL-3.0 | Study only; don't copy code | Comparison |
| [fisharebest/webtrees](https://github.com/fisharebest/webtrees) | Genealogy web engine. | GPL-3.0 | Study only; don't copy code | Comparison |
| [collectiveaccess/providence](https://github.com/collectiveaccess/providence) | Archive cataloguing. | GPL-3.0 | Study only; don't copy code | Partners' systems |
| [omeka/omeka-s](https://github.com/omeka/omeka-s) | Heritage publishing. | GPL-3.0 | Study only; don't copy code | Partners' systems |
| [tropy/tropy](https://github.com/tropy/tropy) | Research photo metadata. | Licence file (type not recognised) | Read the licence file first | Imports |
| [paperless-ngx/paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) | OCR and document management. | GPL-3.0 | Study only; don't copy code | Design reference |
| [archivesspace/archivesspace](https://github.com/archivesspace/archivesspace) | Archival finding aids. | Custom (not recognised) | Read the licence file first | Partners' systems |
| [artefactual/atom](https://github.com/artefactual/atom) | Archival descriptions. | AGPL-3.0 | Study only; don't copy code | Partners' systems |
| [OpenRefine/OpenRefine](https://github.com/OpenRefine/OpenRefine) | Cleaning and reconciliation. | BSD-3-Clause | May reuse with credit, after review | Data cleaning |
| [opensanctions/nomenklatura](https://github.com/opensanctions/nomenklatura) | Entity-resolution decisions. | MIT | May reuse with credit, after review | Merge suggestions |
| [opensanctions/rigour](https://github.com/opensanctions/rigour) | Name normalisation. | MIT | May reuse with credit, after review | Merge suggestions |
| [opensanctions/yente](https://github.com/opensanctions/yente) | Entity matching service. | MIT | May reuse with credit, after review | Merge suggestions |
| [dedupeio/dedupe](https://github.com/dedupeio/dedupe) | Duplicate matching. | MIT | May reuse with credit, after review | Merge suggestions (WP10) |
| [maplibre/maplibre-gl-js](https://github.com/maplibre/maplibre-gl-js) | Web maps (in use). | Licence file (type not recognised) | Read the licence file first | Time map, Lifeline map |
| [openlayers/openlayers](https://github.com/openlayers/openlayers) | Raster map services. | BSD-2-Clause | May reuse with credit, after review | Time map |
| [postgis/postgis](https://github.com/postgis/postgis) | Spatial database. | GPL-2.0 and others | Study only; don't copy code | Later, at scale |
| [protomaps/PMTiles](https://github.com/protomaps/PMTiles) | Tile packaging. | Licence file (type not recognised) | Read the licence file first | Self-hosted tiles |
| [mourner/suncalc](https://github.com/mourner/suncalc) | Sun position. | BSD-2-Clause | May reuse with credit, after review | Photo dating aid |
| [skyfielders/python-skyfield](https://github.com/skyfielders/python-skyfield) | Astronomy. | MIT | May reuse with credit, after review | Photo dating aid |
| [duckdb/duckdb](https://github.com/duckdb/duckdb) | Querying CSV and Parquet. | MIT | May reuse with credit, after review | Data imports |
| [apache/superset](https://github.com/apache/superset) | Admin analytics. | Apache-2.0 | May reuse with credit, after review | Optional |
| [TanStack/table](https://github.com/TanStack/table) | Tables. | MIT | May reuse with credit, after review | Database browser |
| [TanStack/virtual](https://github.com/TanStack/virtual) | Virtualised long lists. | MIT | May reuse with credit, after review | Lifeline rows (WP9) |
| [ProjectMirador/mirador](https://github.com/ProjectMirador/mirador) | IIIF document viewer. | Apache-2.0 | May reuse with credit, after review | Record viewer |
| [UniversalViewer/universalviewer](https://github.com/UniversalViewer/universalviewer) | IIIF viewer. | Custom (not recognised) | Read the licence file first | Record viewer |
| [opensearch-project/OpenSearch](https://github.com/opensearch-project/OpenSearch) | Full-text search at scale. | Apache-2.0 | May reuse with credit, after review | Later |
| [tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract) | Printed text OCR (in use). | Apache-2.0 | May reuse with credit, after review | Document reading |
| [mittagessen/kraken](https://github.com/mittagessen/kraken) | Historical text OCR. | Apache-2.0 | May reuse with credit, after review | Document reading |
| [openai/whisper](https://github.com/openai/whisper) | Speech recognition. | MIT | May reuse with credit, after review | Interviews |
| [ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Local speech recognition. | MIT | May reuse with credit, after review | Interviews |
| [discourse/discourse](https://github.com/discourse/discourse) | Community forums. | GPL-2.0 | Study only; don't copy code | Connect |
| [internetarchive/heritrix3](https://github.com/internetarchive/heritrix3) | Web preservation. | Licence file (type not recognised) | Read the licence file first | Later |
| [internetarchive/bookreader](https://github.com/internetarchive/bookreader) | Digitised book viewer. | AGPL-3.0 | Study only; don't copy code | Later |
| [FamilySearch/GEDCOM](https://github.com/FamilySearch/GEDCOM) | GEDCOM 7 specification and test files. | Apache-2.0 | May reuse with credit, after review | Imports and exports (in use) |
| [statsbomb/open-data](https://github.com/statsbomb/open-data) | Football event data. Now at hudl/open-data. | Licence file (type not recognised) | Read the licence file first | Sport (later) |

### Ideas to borrow (Update 1)

1. Explainable evidence grades (ex-USSR Kinship Research).
2. Places recorded as they were named and governed at the time.
3. Autoplay through time (Time Travel Map: study only, GPL-3.0).
4. Household-based record matching (Irish Genealogy Research Assistant: licence unclear, ideas only).
5. A brick-wall investigation board (TreeMonk: ideas only).

## Changing this list

When a source changes status, update its row here and, where relevant: [DATA_SOURCES.md](DATA_SOURCES.md), `services/api/history/data/sources.json` (the in-product source directory), [CONNECTORS.md](CONNECTORS.md) for keyed connectors, and an ADR in [DECISIONS.md](DECISIONS.md) for anything affecting data rights.
