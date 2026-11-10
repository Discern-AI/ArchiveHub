# ArchiveHub — Development Addendum 3.0 (Consolidated)

**Subtitle:** Person-centred genealogy, historical context, lived experience, cultural history, artistic/literary representations, and illustrated report generation  
**Date:** 10 November 2026  
**Revision:** 3.0 — incorporates Cultural History Engine and additional repositories discussed after v2.0. Original v2 sections retained.  
**Status:** Working product and engineering specification. Proposals and candidate integrations, **not** confirmation of API access, licences, current functionality or completed implementation.  
**Companion:** `ARCHIVEHUB_MASTER_BLUEPRINT.md` (v1.0, 5 November 2026)  
**Audience:** Founder, VS Code coding assistant, engineering collaborators, archivists, prospective data partners.

> **Instruction to implementers:** **Do not replace or discard the original blueprint or existing HTML prototype.** Apply this document as a delta. Preserve the four product areas—**Record, Research, Home, Connect**—the chat-first interface, the Archive Explorer, existing project/file model, source provenance, and default-private access. Where requirements differ, prefer the more explicit data-integrity, permissions, import/export and historical-research requirements in this addendum; record conflicts as architecture decisions.

---

## Contents

1. What changed since the first blueprint
2. Updated product thesis and design requirements
3. User-research findings: experienced genealogy researcher
4. Record 2.0: people, life stories, pictures, trees and migrations
5. GEDCOM, tree migration, merging and evidence validation
6. Historical Context Engine: explaining records and lived conditions
7. Lived Experience Archive: diaries, interviews and questionnaires
8. Historical World Model: expanded data domains and map layers
9. Expanded genealogical and government-record acquisition
10. Education, sport, military service and institutional life
11. Historical photography, astronomy and the reconstruction toolkit
12. Expanded source and connector inventory
13. Open-source software and developer libraries
14. Updated data model, APIs and integration contracts
15. Interface changes for the existing prototype
16. AI orchestration and research-integrity rules
17. Permissions, licensing, privacy and contributor economics
18. Prioritised implementation programme
19. Testing, worked cases and definition of done
20. Outreach, due diligence and unresolved decisions
21. Suggested VS Code implementation prompt
22. Source links and documentation index
23. Cultural History Engine: purpose, evidence rules and entity model
24. Cultural discovery: art, literature, folklore, music and media
25. Expanded cultural sources, APIs and datasets
26. Recently identified GitHub repositories: inventory and adoption assessment
27. Illustrated Historical Report generator: product and technical requirements
28. UI extensions, source rights, micropayments and moderation
29. Phased cultural build, acceptance tests and demonstration scenarios
30. VS Code implementation prompt for the cultural extension
31. Additional cultural documentation and links

---

# 1. What changed since the first blueprint

The consolidated v3.0 addendum retains all v2.0 requirements and appends cultural-history and publishing requirements in §§23–31. In particular, it adds cultural objects to the shared evidence graph, an illustrated long-form report builder, cultural media browser and an evaluated repository catalogue.

The original v1.0 specification already covered the following: one application with Record, Research, Home and Connect; a right-hand Archive Explorer; a source directory and external connector framework; evidence/provenance records; basic GEDCOM import/export; historical mapping; AI-supported research; OCR and oral histories; contributor royalties and optional donations; and a staged technical roadmap. **Those are retained, not rediscovered here.**

Subsequent conversations (5–10 November 2026) added or materially sharpened these ideas:

| Addition or refinement | Why it matters | Proposed home | Priority |
|---|---|---|---|
| Person-centric **Life Story** as a major view | Users want to understand how people lived, not merely browse hints | Record | P0 |
| **Chronological photo gallery** per person | Current genealogy services can attach images awkwardly | Record | P0 |
| **Branch Review** before accepting another user's ancestors | Prevents cascading errors from unverified tree copies | Record | P0 |
| **Tree health, merge safety and orphan detection** | Addresses real problems with legacy genealogy systems | Record | P0 |
| **GEDCOM 5.5.1/7/GedZip pipeline** with round-trip and missing-media report | Transfers existing family research without recreating it | Record | P0–P1 |
| **Family Journey / migration map** | Turns disconnected addresses into navigable life histories | Record + map | P1 |
| **Explain This Record** / historical terminology | Ordinary source labels are often incomprehensible without context | Record + Research | P0–P1 |
| **Institution and occupation histories** | Explain workhouses, schools, military postings, trades, etc. in period-specific terms | Research | P1 |
| **Lived Experience Archive** | Find named mentions and period-comparable testimony in diaries/interviews | Research | P1–P2 |
| **Historical World Model** | Enrich records with economic, property, environmental, social and cultural context | Shared services | P1–P3 |
| **Property and neighbourhood history** | Reconstruct buildings, prices, planning, heritage and residence | Research + map | P1–P2 |
| **Sun/shadow/astronomy module** | Date and orient historical photos cautiously | Media + map | P2 |
| **Museum object library and material culture** | Show equipment, clothing and objects associated with occupations and eras | Research + Home | P2 |
| **Education, sport, and long-tail government sources** | Reveal unusual personal evidence absent from standard genealogy catalogues | Research | P2 |
| **Original-holding-institution source tracing** | Obtain equivalent primary records without relying on Ancestry's proprietary index | Research + commercial | P0 research, P2 partnerships |
| **Source-specific access modes** | Distinguish full record, index, research-only data and external paywall | Connector framework | P0 |
| **Historical qualitative vs demographic comparisons** | Prevent treating sample memories or population averages as an ancestor's experience | AI + evidence | P0 |

**Scope boundary:** This document is an addendum rather than a rewritten v1. Its value lies in concrete new behaviours, schema changes, integration candidates and build order. Avoid duplicating every screen and endpoint already specified in v1.

# 2. Updated product thesis and design requirements

## 2.1 Product thesis

**ArchiveHub should convert fragmented historical evidence into an intelligible reconstruction of people, places and their lived worlds—while maintaining a clear boundary between primary facts, contextual comparisons and interpretations.**

The research chain is:

1. **Find:** locate a document or named mention across sources.
2. **Read:** view the underlying scan/transcript/index, not only an AI summary.
3. **Understand:** explain contemporary terminology, institutions, conditions and why a record exists.
4. **Relate:** connect people, places, events, occupations and records with explicit evidence grades.
5. **Visualise:** life story, photos, timeline, family tree, historical map and migration route.
6. **Preserve:** save sources, user edits, proof and research questions in a portable private archive.
7. **Share:** publish only material explicitly approved and licensed by the relevant parties.

## 2.2 New requirements for all four areas

- A source opened in Archive Explorer can become a contextual explanation, an entity assertion, a map pin, a story event or a draft article **without losing its original citation**.
- The assistant distinguishes **a named individual's documented experience**, **testimony of comparable people**, and **aggregate historical conditions**.
- Research activities must remain useful without AI chat: browsing, selecting, highlighting, correcting, saving and exporting records.
- Users can browse external catalogues without implying full-text access or rights to reproduce images.
- Avoid endless hint cascades: imported relationships are proposed, not automatically verified.
- A locally uploaded document or family tree remains private unless explicitly shared; the platform may not train on it simply because it is uploaded.
- A commercial provider's API, a free public website, and a repository containing only code must be labelled differently in the source directory.

# 3. User-research findings: experienced genealogy researcher

**Basis:** A transcript of the founder's sister describing extended use of Ancestry and other genealogy websites. This is a qualitative interview, not a statistically representative survey. Specific competitor behaviour is based on her recollection and should be tested against current products before asserting it as fact.

## 3.1 Problems reported

1. Copying another person's large family branch or accepting batches of hints may introduce mistaken ancestors and many inadequately evaluated supporting documents.
2. Profiles often emphasise discrete facts and records rather than constructing a readable chronology of work, relationships, locations and life events.
3. Photos are cumbersome to add or browse; she wants a **scrollable person-level gallery** with contextual snippets.
4. One unidentified alternative genealogy product seemed to build a pre-existing ancestral branch rapidly and felt better validated, but lacked well-presented media. **Do not attribute this comparison to a named product without checking.**
5. Older tree structures and awkward deletion/merge behaviour can leave disconnected individuals or errors.
6. External-record sources are not always displayed seamlessly or attractively.
7. Family migration, place changes and residential moves are not presented together as an intuitive narrative.
8. Census and institution records may be incomprehensible until the user undertakes separate historical research.

## 3.2 User jobs to implement

- “Tell me the life of this person using **only** confirmed facts, and show me where I can read the evidence.”
- “What did ‘cordwainer’ or ‘pauper apprentice’ mean here in 1790?”
- “Show the photos associated with this person, grouped by decade, with other people and places linked.”
- “I imported 2,500 people. Show likely duplicate records, unsupported branches and disconnected relatives.”
- “Show all documented homes and movements for the maternal line between 1820 and 1950.”
- “Preview these 30 proposed ancestors before adding the branch.”

## 3.3 Product validation programme

Test these workflows with the original interviewee and at least four other genealogists of varied experience. Measure whether users can: (a) spot a deliberately unsupported link; (b) locate original evidence from a biography; (c) correctly understand a historical term; (d) browse a gallery; (e) reverse a faulty merge; (f) distinguish a documented move from an inferred journey. Record failures before building optional enhancements.

# 4. Record 2.0: people, life stories, pictures, trees and migrations

## 4.1 A person has four first-class views

- **Life Story:** prose narrative constructed from dated events, attributed evidence and contextual notes. Every substantive biographical claim exposes its supporting record or uncertainty.
- **Timeline:** chronological family, occupation, address, education, military, health (if rights allow), institution, migration, marriage and death events. Support approximate and conflicting dates.
- **Gallery:** scrollable images and media associated with the person, optionally organised by date, location, event or collection. Distinguish “image depicts this person” from “image illustrates the era/occupation/location”.
- **Tree & Evidence:** interactive family links, alternative candidate relatives, full source citations, original record views and explicit conflict resolution.

Switching views preserves the active person, selected year and research state. Chat can open any view and highlight source-specific items in it.

## 4.2 Life Story generation

Inputs: linked event assertions, source documents, oral histories, quotations, and optional contextual sources. Outputs: short biography, detailed biography, life chapters, or a source-by-source fact chronology.

Suggested story sections: early life; household/family; work and education; places lived; institutional/military experience; major transitions; later life; unresolved questions. Never force sections absent evidence.

Each passage has a claim list. The user can open the passage's source panel, mark a claim as disputed, change its wording, remove it or attach a better source. Re-running AI narration **must not overwrite manual edits** without approval.

### Story evidence labels

- `documented`: direct testimony or primary source establishes the claim (with possible transcription caveats).
- `corroborated`: two or more independent sources support a claim.
- `reported`: attributed statement, including a memory or external family tree, not independently confirmed.
- `contextual`: a period-wide or location-wide condition, not direct evidence about this person.
- `inferred`: proposed relationship, date or interpretation with rationale.
- `unresolved`: competing alternatives or insufficient evidence.

These are editorial labels, not machine-generated numerical probabilities of identity.

## 4.3 Photo / media requirements

- Original image preserved with checksum; derivative thumbnails and display sizes stored separately.
- EXIF, upload source, written date, estimated date and place captured independently.
- Media is many-to-many: one photo can be related to multiple people, places, events and projects.
- People tags and “depicts” links require review; modern facial identification across third-party archives is not an MVP.
- Gallery filters: portraits; group photos; houses; workplaces; places; documents; maps; context-only images; unknown date.
- Hover/click opens caption, original citation, location and source rights.
- Group photos may support manually placed bounding-box labels without automatic person identification.
- A related historical photo of a street must not be presented as a confirmed image of a specific person's home without evidence.

## 4.4 Family Journeys and historical migration

The map displays **observed** residence/appearance events, not automatically assumed travel routes. Users may choose person, household, branch or generation as the unit.

- Plot point: `person_id`, `place_id`, event type, date interval, original place-string, geocoding precision, source_id.
- Distinguish birth location, residence, employment, military station, travel destination, burial and uncertain mention.
- Permit side-by-side family branches and a timeline slider.
- Optionally propose plausible historic travel networks but label routes as hypothetical unless documented.
- Support historically varying place names and administrative boundaries; geocoded street centres are not equivalent to exact historical house locations.
- Explain gaps, for example “recorded in Somerset in 1861 and Bristol in 1871; intervening route and move date unknown.”

# 5. GEDCOM, tree migration, merging and evidence validation

## 5.1 Standards and scope

Support **GEDCOM 5.5.1**, **FamilySearch GEDCOM 7** and **GedZip** as separate import profiles. Confirm exact dialect/extension support by tests. GEDCOM exchange is not a complete export of an account's historical-record images, hints, private messaging or licensed media.

Reference: <https://github.com/FamilySearch/GEDCOM> and <https://gedcom.io/>.

## 5.2 Import workflow

1. Upload `.ged` or supported packaged file into a **private staging area**.
2. Detect encoding, GEDCOM version and vendor-specific extensions without silently discarding unknown fields.
3. Validate references, family associations, duplicate IDs, dates, source citations, notes and media paths.
4. Show an import manifest: individuals, families, events, source objects, references, notes, media available, missing media, unrecognised tags, parsing errors and proposed warnings.
5. Import as a new tree or propose merge into an existing tree; provide preview and rollback plan.
6. Preserve source GEDCOM and a canonical parse manifest; maintain external import identifiers.
7. Export to GEDCOM 7 and test round-trip with known sample trees; declare which fields are lossy.

Do not automatically copy media referenced by arbitrary external URLs unless authorised, safe and technically available.

## 5.3 Tree health and Branch Review

Tree health detects: impossible chronology; repeated identities; duplicate relatives; orphaned links; contradictory dates and places; source-less claims; too many descendants for plausible dates; imported facts lacking original citations; endogamy-related ambiguity and multiple connections.

**Branch Review** presents a candidate branch in staging, with each relationship individually linked to evidence and confidence/rationale. Choices: accept all **supported** links, accept selected links, keep as hypothesis, reject, or ask for more evidence. “Accept all” cannot bypass explicit review when important links are unsupported.

## 5.4 Reversible merging and deletion

- Use a graph transaction and preserve both original entity IDs as historical aliases where appropriate.
- Record a reversible event history (`merge`, `split`, `unlink`, `delete soft`, `restore`) and link consequences.
- Before merge/delete show affected partners, parents, children, events, sources, media and shared projects.
- Validate no unintended orphaning; allow non-destructive deactivation for dubious people.
- Keep source contradictions even if a preferred display value is selected.

**Implementation candidates:** Gramps Desktop/Web/API, webtrees, GeneWeb. These are alternative engines or interoperability targets; don't deploy all of them as competing masters.

# 6. Historical Context Engine: explaining records and lived conditions

## 6.1 Originating use case

The founder described two brothers in late-eighteenth-century Wiltshire/Swindon-linked records, whose mother apparently placed them in an institution; she later took them out, and their adult lives diverged, with one joining the army. The institution's exact name, registration dates and document contents **have not been supplied or independently verified**. Treat this as a **research-test scenario**, not a confirmed historical reconstruction. In particular, avoid asserting that it was a post-1834 workhouse or that the mother's motive was poverty without source evidence.

## 6.2 “Explain This Record” feature

Available from a selected document, field, unfamiliar word, name, occupation, institution, place or event.

Response structure:

1. **Literal reading:** transcribed text or index entry, with manuscript location and OCR uncertainty.
2. **Terminology:** what the term meant in the record's jurisdiction and decade; how meaning changed.
3. **Institution:** the precise body, its historical names, purpose and operation dates; distinguish similarly named organisations.
4. **Historical practice:** what the record type normally represents and which related records were generated.
5. **Individual implication:** what this document actually supports about the named person.
6. **Comparable life:** period- and location-appropriate first-person accounts from other people, clearly marked as comparisons.
7. **Broader context:** laws, occupations, conditions, contemporary statistics and scholarship.
8. **Open questions:** unknown motives, ambiguities, missing documents, alternate explanations.
9. **Research trail:** next relevant archives, catalogue queries and record series.

### Period-sensitive explanation

Workhouses, poorhouses, schools, asylums, military units and courts changed function over time and region. A pre-1834 English Poor Law reference cannot be explained exclusively through the New Poor Law system. Preserve legal jurisdictions (England/Wales, Scotland, Ireland, colonial contexts).

## 6.3 Context taxonomy

Build curated `historical_concepts` with versioned time/place scope:

- Institutions: parish poorhouse, workhouse, charitable school, prison, asylum, hospital, military depot, school, trade guild.
- Occupations: agricultural labourer, cordwainer, charwoman, journeyman, railway worker, engine tenter and period-specific categories.
- Laws/practices: Old and New Poor Law, settlement and removal, parish apprenticeship, military recruitment, registration requirements.
- Social life: childhood, household structures, food, transport, literacy, leisure, worship and schooling.
- Measures: historical currency, weights, distance, prices and wages, with conversion assumptions.
- Geography: parish, county, poor-law union, borough, ward, changing boundaries and historical toponyms.
- Medicine: historical diagnosis names and institutions, avoiding unsupported personal-health inferences.

Each concept links to time ranges, jurisdiction, explanatory prose, scholarly references, illustrative images and authoritative archives. Historical terminology can have several senses; never choose a meaning solely from a keyword.

## 6.4 Context assertions and citations

A quoted contemporary account must be attributed to the author, date of writing, period discussed and collection. A typical wage estimate must have its geography/population/year and must never be treated as that ancestor's wage. Treat interpretations as revisable hypotheses.

**Candidate sources:** British History Online / Victoria County History, The National Archives research guides, Mass Observation, UK Data Service, CAMPOP, local history centres, workhouses.org.uk (secondary source, permission for reuse needed), scholarly publications, historical dictionaries and explanatory records.

# 7. Lived Experience Archive: diaries, interviews and questionnaires

## 7.1 Two distinct research functions

**A. Named evidence discovery:** find appearances of named individuals, places, addresses, workplaces, schools, clubs and institutions in transcripts, letters, interviews, diaries, questionnaires, newspapers and archival catalogues.

**B. Comparable contemporary description:** retrieve and synthesise first-person accounts of work, family, poverty, war, housing, migration and social conditions among comparable populations, without asserting that a particular ancestor experienced the same events.

These two functions must use separate ranking and disclosure rules. A statement by an unrelated diarist cannot establish an individual's biography.

## 7.2 Data types and metadata

- Diary: entry date, diary author, period described, place, page image, copyright and restrictions.
- Interview: recording date, interviewee, interviewer, audio timestamp, speaker labels, retrospective period described, transcript provenance and consent.
- Questionnaire: date, question text, respondent category, recruitment/sample description, original response text and usage rights.
- Letter: date written, origin/destination, sender, recipient, transcription, envelope/postmark, collection and restrictions.
- Oral recollection: date of event (possibly uncertain) **distinct** from date of narration.
- Survey dataset: sample methodology, waves, variable dictionary, population, anonymisation level and permitted output.

Index `recorded_at`, `describes_start`, `describes_end`, `location_scope` and `participant_privacy` independently.

## 7.3 Collections to evaluate

| Resource | Material | Proposed initial access | Principal constraint |
|---|---|---|---|
| Mass Observation (<https://www.massobs.org.uk/>) | Diaries, questionnaires, observations, volunteer accounts; originated 1937; revived 1981 | Catalogue/discovery; partnership discussions | Digital content is not wholesale open for commercial reuse |
| The Great Diary Project (<https://thegreatdiaryproject.co.uk/>) | Thousands of unpublished private diaries | Collection-level discovery; partnership | Reading-room material and personal privacy, no automatic bulk rights |
| National Life Stories / British Library (<https://www.bl.uk/>) | In-depth oral-history interviews | Public catalogues, permitted listening/transcript links | Online access and reproduction vary by collection |
| Millennium Memory Bank | Late-1990s interviews about twentieth-century lives | Descriptive linking and access enquiry | BBC/British Library rights and access restrictions |
| UK Data Service qualitative data (<https://ukdataservice.ac.uk/>) | Interviews, focus groups, historic social studies, some searchable transcripts | Dataset-by-dataset research access | Participant consent, restricted access, no reidentification |
| *Family Life and Work Experience Before 1918* / *The Edwardians* | Retrospective accounts of earlier life collected in the 1970s | UK Data Service catalogue and permitted research versions | Reuse and participant restrictions |
| *Family and Kinship in East London* research | 1950s family/community interviews and survey material | Catalogue/archive enquiry | Raw notes and dataset access vary |
| East Midlands Oral History Archive (<https://le.ac.uk/emoha/catalogue>) | Regional oral histories | Catalogue and selected online material | Transcript/audio rights vary |
| London Museum / Bishopsgate Institute | London workplace and community testimony | Catalogues and agreements | Restrictions vary |
| London Lives (<https://www.londonlives.org/>) | Name-rich eighteenth-century records of ordinary lives | Search and linked references | Check download, text reuse and citation conditions |
| Digital Panopticon (<https://www.digitalpanopticon.org/>) | Linked criminal and life-history records | Methodological reference, permitted data | Identity reconciliation uncertainty, rights |
| Reading Experience Database (<https://www.open.ac.uk/Arts/reading/UK/>) | Diaries, letters and other evidence of reading | Structured source discovery | Check extract and bulk-reuse terms |
| Europeana 1914–1918 (<https://www.europeana.eu/>) | Family-contributed letters, diaries and WWI items | Europeana Search API + rights-aware source links | Rights vary at item level |
| Imperial War Museums (<https://www.iwm.org.uk/collections>) | Wartime testimony, private papers, diaries | Catalogue discovery | Media/record rights |
| Local museums and societies | Small oral-history/letter collections | Manual onboarding and permissions | Uneven digitisation, consent and metadata |

**Important:** This table is a *candidate inventory*. It does not claim all material is indexed, accessible via API, or commercially licensable.

## 7.4 UI: a testimony comparison view

Right-hand panel tabs: `Source scan/audio`, `Transcript`, `Mentions`, `Context`, `Map`, `Compare`, `Save`.

When answering “What was domestic service like in Berkshire in 1901?”, show accounts by source type and place: contemporary diary vs 1970s recollection vs historian's study. Include sample bias and how representative the source is. Provide time-offset and playback from the quoted transcript passage where the archive authorises it.

## 7.5 Own oral-history collection programme

Local societies and family users can run consent-based interview projects. Provide interview question templates, recordings, transcription, correction, review, participant approvals, visibility tiers and embargoes. Consent applies at the recording/transcript/publication level and can be more restrictive than the account's general profile settings. Avoid automatic publication of names/identifiable statements about living third parties.

# 8. Historical World Model: expanded data domains and map layers

The v1 map and evidence graph evolve into a **Historical World Model**, a research-enrichment service rather than a fifth customer-facing product area.

## 8.1 Dimensions

| Domain | Types of source | Example output |
|---|---|---|
| Property / housing | Property sales, planning, historic directories, rate books, tithe maps | Address/building chronology |
| Financial / economic | Interest rates, wages, price indices, insolvencies, bank history | What money/wages meant in a given era |
| Industry / employment | Trade directories, factory records, CAMPOP occupations, company filings | Economic context of a job/location |
| Weather / climate | Met Office observations, HadUK-Grid, ERA5 reanalyses, historical floods | Conditions near a documented event (observation vs reconstruction) |
| Sun / astronomy | SunCalc, Skyfield, NASA eclipses | Shadow direction and plausible time of day |
| Museum objects / material culture | Museum object APIs, Science Museum, V&A, Europeana | Historical objects associated with occupations |
| Demography / society | ONS, NOMIS, UKDS, cohort studies, Our World in Data | Household and social conditions with period/population labels |
| Courts / crime / justice | Old Bailey, Gazette, archives, historical prison catalogues | Legal and institutional biography |
| Education | School registers, logbooks, university archives, school histories | Education chronology and institution descriptions |
| Sport / leisure | Historic football results, cricket scorecards, sports museums, local newspapers | Clubs, grounds, individual named mentions |
| Transport / migration | Old railways, canals, passenger lists, ports, geographic networks | Plausible transport infrastructure around documented moves |
| Environmental / archaeological | Historic England, ADS, geology, rivers, habitats | Evolving landscape and settlements |
| Literature / language | Books, historic dictionaries, personal reading testimony | Literary geography, period meanings |
| Military service | National Archives, MOD, CWGC, service museum and regiment collections | Service chronology plus unit-level context |

## 8.2 Context service contract

Input: entity or location, time range, question, requested domain, source-access rights.  
Output: dated data series or testimony with `dataset_id`, `unit`, `geographic_scope`, `temporal_scope`, `sample_or_population`, `source_kind`, `observation_vs_model`, `licence`, `citation`, `uncertainty_note`.

A contextual overlay must not silently become a person fact. “The national infant mortality rate was X in year Y” is a place/time context statement; it cannot be turned into a claim about an ancestor's children.

## 8.3 Property and neighbourhood explorer

Prototype workflow: enter historical or current address, locate it approximately, show available historical OS maps, historic place names, conservation/listed-building status, planning applications, post-1995 sale history and geotagged photos. Time-filter every layer and explicitly display coverage gaps.

**Caution:** modern property sale and planning records should not be treated as historical ownership proof or an automatically reliable means of identifying living occupants.

## 8.4 Historical map operating rules

- Maps have acquisition, survey and publication dates, which may differ from chosen target year.
- Historical boundaries and names must not be replaced silently with current equivalents.
- Geographic precision must be represented: exact building, parcel, street, parish, settlement, county or approximate region.
- Include layer attributions and source restrictions.
- Users can save map evidence into a research basket with the exact layer, feature, time and source.

# 9. Expanded genealogical and government-record acquisition

## 9.1 Original-source strategy

The goal is **the same underlying historical evidence**, not an unauthorised clone of Ancestry/Findmypast proprietary images, transcriptions and hints. Research each major collection's chain: original custodian → digitisation contractor → indexer → web distributor → commercial reuse terms.

ArchiveHub should record five different access states:

1. `OPEN_DOWNLOAD` — downloadable dataset with confirmed compatible reuse terms.
2. `PUBLIC_API` — publicly documented API, subject to published rate and licensing constraints.
3. `PARTNER_API` — contract, approval or authentication required.
4. `RESEARCH_RESTRICTED` — secure research/specified purposes, **not** a public person-search index.
5. `LINK_ONLY` — legal discovery page; no authorised programmatic full text.

An accessible web form or publicly viewable scan **does not imply** automated harvesting or commercial republication rights.

## 9.2 Core UK person-record sources

| Collection / institution | Relevant records | Initial route | Open issues |
|---|---|---|---|
| General Register Office England/Wales (<https://www.gro.gov.uk/>) | Civil birth, marriage, death registrations from 1837 | Official index discovery and ordering guidance | Bulk terms, digital image access, recent-record restrictions |
| FreeBMD (<https://www.freebmd.org.uk/>) | Volunteer-transcribed civil registration indexes | Partner/bulk-access discussion | Permission for commercial redistribution |
| FreeREG (<https://www.freereg.org.uk/>) | Baptisms, marriages, burials | Partnership and source discovery | Coverage varies, bulk terms |
| FreeCEN (<https://www.freecen.org.uk/>) | Census transcriptions | Partnership and source discovery | Coverage, licensing |
| FamilySearch (<https://developers.familysearch.org/>) | Family Tree, place data and supported historical records | Approved API relationship | Production approval, record-specific access |
| ScotlandsPeople (<https://www.scotlandspeople.gov.uk/>) | Scottish civil, parish, wills, valuation etc. | Official search and purchases | Reuse and paid-media terms |
| IrishGenealogy.ie (<https://www.irishgenealogy.ie/>) | Irish civil and church records | Official service and permitted links | Rights/coverage |
| GRONI (<https://www.nidirect.gov.uk/>) | Northern Irish civil records | Official access | Account, record cutoffs and fees |
| National Archives Discovery (<https://discovery.nationalarchives.gov.uk/>) | Archive descriptions, military, government and specialist series | API/requested access | Descriptions ≠ full documents |
| UK Data Service I-CeM (<https://ukdataservice.ac.uk/>) | Historic census microdata | Research application, aggregate analysis | Named/address-level data restricted; NOT public API |
| CWGC (<https://www.cwgc.org/>) | War casualties, commemorations and grave locations | Search/partnership | Data reuse and images |
| National Records of Scotland (<https://www.nrscotland.gov.uk/>) | Historic Scottish records | Official discovery | Dataset-specific access |
| The Gazette (<https://www.thegazette.co.uk/>) | Bankruptcies, probate, promotions, legal notices | Structured/open search endpoints | Query limits, rights |
| Find a Grave (<https://www.findagrave.com/>) | Memorial data and user images | Search links/partnership | Contributor copyrights, privacy, no assumed scraping |
| Companies House (<https://developer.company-information.service.gov.uk/>) | Company filings, officers and status | Public developer API | Historical coverage and living-person privacy |

## 9.3 Military records programme

- Original record sources: The National Archives, MOD, regimental institutions, IWM, National Army Museum, RAF Museum, National Museum of the Royal Navy, CWGC.
- Seek individual records, unit histories, postings, medals, war diaries, photographs and official announcements in separate collections.
- Support a **military chronology** with `enlistment`, `unit`, `rank`, `posting`, `discharge`, `casualty`, `medal`, `cemetery`, `service_number` with access controls.
- If unit X was at battle Y, mark that as **unit context**, not proof that an individual fought there. Service records are subject to living-person/next-of-kin restrictions.

## 9.4 University and government dataset discovery

- Search university archive catalogues, research data repositories and Jisc Archives Hub.
- Catalogue school registers, university admissions, alumni lists, occupational studies, historical statistics, cohort datasets, courts, immigration and sport.
- Cohort datasets for 1946, 1958, 1970 and later offer *aggregate or authorised research comparisons*, not a method to identify or search participant names.
- Introduce a `restricted_dataset` marker throughout the source registry and prohibit matching protected participant data to living people.

# 10. Education, sport, military service and institutional life

## 10.1 Education

School histories should include historical school names, type, location, opening/closing, authority and archival custodian. Record evidence may include admission registers, attendance logs, school magazines, yearbooks, examination notices, university matriculation and teacher records. Search source catalogues first; do not presume school-level data is available as an API.

## 10.2 Sport

Sport creates dated, person-rich evidence: club membership, results, team lists, newspaper reports, scorecards, venue histories and photographs. Candidate datasets: <https://github.com/jalapic/engsoccerdata>, <https://github.com/openfootball>, <https://github.com/statsbomb/open-data>, <https://cricsheet.org/>, and relevant sporting museums. Some GitHub datasets are third-party compilations and need independent licence/coverage checks. Do not imply that team results establish an ancestor's participation without a named source.

## 10.3 Businesses, bankruptcy and occupational life

Combine company registration, trade directories, historical advertisements, The Gazette, Insolvency Service statistics, old rate books and estate insurance archives. Keep a clear divide between **named bankruptcy notices** and **aggregate bankruptcy rates**. Property and insurance information relating to living people requires heightened privacy scrutiny.

# 11. Historical photography, astronomy and the reconstruction toolkit

## 11.1 Sun and shadow module

Use <https://github.com/mourner/suncalc> for lightweight solar/lunar position and <https://github.com/skyfielders/python-skyfield> for more advanced astronomy. Inputs: geolocation, candidate date/date range, camera-facing direction if established, estimated shadow direction, time-zone rules, calendar conventions and image confidence. Output: possible solar azimuth and altitude, time-of-day intervals, candidate dates, explicitly not a guaranteed photo date.

## 11.2 Historical environment and weather

Candidate sources: Met Office observations, HadUK-Grid, CEDA/MIDAS, NOAA, Copernicus ERA5, Open-Meteo historical API. Label `observed_station`, `gridded_estimate`, `reanalysis`, or `derived` and cite station/dataset, resolution and model uncertainties. Commercial Open-Meteo terms must be checked.

## 11.3 Museum objects and illustrations

Context image results should distinguish **object used by ancestor (documented)** vs **representative object from the period**. Search museum collections through the Met Museum API, V&A, Art Institute of Chicago, Europeana, Smithsonian, UK Museum Data Service, Science Museum Group, IWM and institutional IIIF manifests; verify item-level rights.

## 11.4 Historic footage

Catalogue-first links to BFI, British Pathé, BBC and local community recordings; avoid extracting or redistributing restricted broadcast video without permission. Image geolocation, place comparisons and period-specific scene annotation can be offered independently of identifying individuals in crowds.

# 12. Expanded source and connector inventory

**Reading this table:** `API` = advertised API candidate; `Download` = public files/datasets for some material; `Catalogue` = discovery, not necessarily full text; `Partner` = requires approval or agreement; `Reference` = human-readable site with no presumed general-purpose API. Availability, terms and prices must be revalidated before implementation.

| Domain | Source | URL | Candidate route | Suggested feature |
|---|---|---|---|---|
| Archives | The National Archives Discovery | https://discovery.nationalarchives.gov.uk/ | API / access enquiry | UK archival search |
| Archives | Jisc Archives Hub | https://archiveshub.jisc.ac.uk/ | Catalogue | University holdings discovery |
| Archives | Archives Portal Europe | https://www.archivesportaleurope.net/ | Catalogue / integration assessment | Cross-border discovery |
| Heritage | Europeana APIs | https://api.europeana.eu/ | API key / OAI-PMH | Museum and digitised object search |
| Heritage | UK Museum Data Service | https://museumdata.uk/using-data/our-apis/ | Public/partner APIs | UK objects and museums |
| Heritage | V&A Collections | https://developers.vam.ac.uk/ | API | Material culture |
| Heritage | Metropolitan Museum of Art | https://metmuseum.github.io/ | API | Historical objects |
| Heritage | Art Institute of Chicago | https://api.artic.edu/docs/ | API / download | Historical art |
| Heritage | Smithsonian Open Access | https://www.si.edu/openaccess | API / download | Objects, 3D, specimens |
| Heritage | Rijksmuseum Data | https://data.rijksmuseum.nl/ | API / data | Dutch/European material |
| Heritage | Historic England open data | https://historicengland.org.uk/listing/the-list/data-downloads/ | GIS/download | Listed sites |
| Heritage | Archaeology Data Service | https://archaeologydataservice.ac.uk/ | Catalogue / datasets | Archaeology |
| Geo | NLS historical maps | https://maps.nls.uk/ | Licensed tiles / viewer | Historic basemaps |
| Geo | GB1900 / Vision of Britain | https://www.visionofbritain.org.uk/ | Selected downloads / licence | Historical names and statistics |
| Geo | OpenHistoricalMap | https://www.openhistoricalmap.org/ | Data / tiles | Temporal geography |
| Geo | World Historical Gazetteer | https://www.whgproject.org/ | API/download assessment | Historical place identities |
| Geo | Ordnance Survey OpenData | https://www.ordnancesurvey.co.uk/products/os-open-data | Download | Modern geospatial foundation |
| Geo | GeoNames | https://www.geonames.org/ | API / download | Toponym alternatives |
| Property | HM Land Registry Price Paid | https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads | Download | Property sales since 1995 |
| Property | Land Registry Data Services | https://use-land-property-data.service.gov.uk/ | Account / API | Land and property datasets |
| Planning | Planning Data England | https://www.planning.data.gov.uk/ | API / bulk | Planning boundaries/constraints |
| Planning | UK PlanIt | https://www.planit.org.uk/ | API | Historic planning applications |
| Economy | Bank of England Research Datasets | https://www.bankofengland.co.uk/statistics/research-datasets | Download | Long-run economic indicators |
| Economy | Bank of England IADB | https://www.bankofengland.co.uk/boeapps/database/ | Download/API assessment | Interest/currency series |
| Economy | FRED | https://fred.stlouisfed.org/ | API key | Time series |
| Economy | MeasuringWorth | https://www.measuringworth.com/ | Reference / licence | Historical money comparison |
| Economy | Macrohistory JST | https://www.macrohistory.net/ | Download | Housing, banking, credit history |
| Economy | Insolvency Service statistics | https://www.gov.uk/government/collections/insolvency-service-official-statistics | Download | Bankruptcy rates |
| Economy | Companies House | https://developer.company-information.service.gov.uk/ | API key | Business histories |
| Economy | The Gazette | https://www.thegazette.co.uk/ | API / linked data | Official life notices |
| Weather | Met Office historical station data | https://www.metoffice.gov.uk/research/climate/maps-and-data/data | Downloads | Observed weather |
| Weather | HadUK-Grid | https://www.metoffice.gov.uk/research/climate/maps-and-data/data/haduk-grid | Download | UK historical climate |
| Weather | CEDA archive | https://catalogue.ceda.ac.uk/ | Archive downloads | Historic meteorology |
| Weather | Open-Meteo historical | https://open-meteo.com/en/docs/historical-weather-api | API / commercial terms | Reanalysed climate |
| Weather | Copernicus CDS | https://cds.climate.copernicus.eu/ | API credentials | Reanalysis |
| Weather | NOAA NCEI | https://www.ncei.noaa.gov/ | API/download | Observations |
| Weather | Environment Agency data | https://environment.data.gov.uk/ | Open API | Floods and rivers |
| Statistics | ONS API | https://developer.ons.gov.uk/ | Public API | Census aggregates and economy |
| Statistics | NOMIS | https://www.nomisweb.co.uk/ | API | Labour/population |
| Statistics | UK Data Service | https://ukdataservice.ac.uk/ | Research access | Historic census and cohorts |
| Statistics | Our World in Data | https://ourworldindata.org/ | Download | Global comparisons |
| Statistics | Gapminder | https://www.gapminder.org/data/ | Download | Long-run indicators |
| Context | British History Online | https://www.british-history.ac.uk/ | Reference / licence | Place and institution histories |
| Context | Victoria County History | https://www.history.ac.uk/research/victoria-county-history | Publications | Local histories |
| Context | CAMPOP | https://www.campop.geog.cam.ac.uk/research/occupations/datasets/ | Research downloads | Occupations/population |
| Context | Workhouses | https://www.workhouses.org.uk/ | Reference / permission | Poor Law institutions |
| Context | Old Bailey Online | https://www.oldbaileyonline.org/ | Research access | Court narratives |
| Context | London Lives | https://www.londonlives.org/ | Search / terms check | Named ordinary people |
| Context | Reading Experience Database | https://www.open.ac.uk/Arts/reading/UK/ | Search | Literary references in diaries |
| Genealogy | GRO | https://www.gro.gov.uk/ | Official search/purchase | BMD |
| Genealogy | FreeBMD | https://www.freebmd.org.uk/ | Search / partner | BMD indexes |
| Genealogy | FreeREG | https://www.freereg.org.uk/ | Search / partner | Parish records |
| Genealogy | FreeCEN | https://www.freecen.org.uk/ | Search / partner | Census transcriptions |
| Genealogy | FamilySearch developers | https://developers.familysearch.org/ | Approved API | Trees/places/records |
| Genealogy | ScotlandsPeople | https://www.scotlandspeople.gov.uk/ | Official search | Scottish records |
| Genealogy | IrishGenealogy.ie | https://www.irishgenealogy.ie/ | Official search | Irish BMD |
| Genealogy | CWGC | https://www.cwgc.org/ | Search / partner | Casualties and graves |
| Military | IWM Collections | https://www.iwm.org.uk/collections | Catalogue | War objects and testimony |
| Military | MOD service record guidance | https://www.gov.uk/get-copy-military-records-of-service | Official application | Service records |
| Education | Get Information About Schools | https://get-information-schools.service.gov.uk/ | Data/download assessment | Historic school identifiers |
| Education | HESA | https://www.hesa.ac.uk/ | Data products / licence | Higher education context |
| Sports | Engsoccerdata | https://github.com/jalapic/engsoccerdata | Repo/download | Football timeline |
| Sports | OpenFootball | https://github.com/openfootball | Repo/download | Results |
| Sports | Cricsheet | https://cricsheet.org/ | Download | Cricket results |
| Sports | Olympedia | https://www.olympedia.org/ | Reference / terms | Olympic biographies |
| Culture | Open Library | https://openlibrary.org/developers/api | API | Books and editions |
| Culture | Google Books | https://developers.google.com/books/docs/v1/using | API | Book metadata |
| Culture | Project Gutenberg | https://www.gutenberg.org/ | Download / rights | Historic writing |
| Culture | Internet Archive | https://archive.org/ | API / item licence | Book and AV discovery |
| Culture | HathiTrust | https://www.hathitrust.org/ | Partner/research | Digitised books |
| Government | UK API Catalogue | https://www.api.gov.uk/ | Directory | Discover further public APIs |
| Computation | Wolfram Alpha APIs | https://products.wolframalpha.com/api/ | Commercial API | Calculations |
| Astronomy | SunCalc library | https://github.com/mourner/suncalc | Local code | Sun/shadows |
| Astronomy | Skyfield | https://github.com/skyfielders/python-skyfield | Local code | Ephemerides |

## 12.1 Source registry evaluation fields

Add `data_form` (`raw_records`, `transcriptions`, `index`, `catalogue`, `aggregate`, `research_sample`, `software_only`), `rights_status`, `commercial_reuse`, `search_capabilities`, `time_coverage`, `geographic_coverage`, `personal_data_risk`, `bulk_access`, `access_cost`, `attribution`, `source_organisation`, `record_owner`, `digital_publisher`, `original_custodian`, `partnership_contact`, `last_verified`.

The **last_verified** field is mandatory for claims about current APIs, pricing and public access. Set to `null` if not validated.

# 13. Open-source software and developer libraries

These are candidates for evaluation, not a directive to install all components or copy GPL/AGPL software into one proprietary codebase. Read each licence and integration boundary.

| Component | Repository | Use | Decision |
|---|---|---|---|
| GEDCOM spec | https://github.com/FamilySearch/GEDCOM | Format and test fixtures | Adopt standard |
| Gramps Desktop | https://github.com/gramps-project/gramps | Genealogy data model | Evaluate |
| Gramps Web | https://github.com/gramps-project/gramps-web | Tree UI and interaction patterns | Evaluate |
| Gramps Web API | https://github.com/gramps-project/gramps-web-api | Genealogy backend | Evaluate integration and licence |
| webtrees | https://github.com/fisharebest/webtrees | Alternative genealogy engine | Compare |
| GeneWeb | https://github.com/geneweb/geneweb | Large genealogy trees | Compare |
| CollectiveAccess Providence | https://github.com/collectiveaccess/providence | Archivist catalogue | Consider partner/standalone |
| Omeka S | https://github.com/omeka/omeka-s | Heritage publication | Consider integration |
| Tropy | https://github.com/tropy/tropy | Research photo metadata | Import/interoperability reference |
| Paperless-ngx | https://github.com/paperless-ngx/paperless-ngx | OCR/document management | Borrow design/integrate where appropriate |
| ArchivesSpace | https://github.com/archivesspace/archivesspace | Finding aids | Interoperability |
| AtoM | https://github.com/artefactual/atom | Archival descriptions | Interoperability |
| OpenRefine | https://github.com/OpenRefine/OpenRefine | Cleaning/reconciliation | Supporting tool |
| Nomenklatura | https://github.com/opensanctions/nomenklatura | Entity-resolution decisions | Evaluate generic methods |
| Rigour | https://github.com/opensanctions/rigour | Name-normalisation | Evaluate |
| Yente | https://github.com/opensanctions/yente | Entity matching/reconciliation | Evaluate |
| Dedupe | https://github.com/dedupeio/dedupe | Duplicate matching | Evaluate |
| MapLibre GL JS | https://github.com/maplibre/maplibre-gl-js | Web maps | Evaluate as primary UI |
| OpenLayers | https://github.com/openlayers/openlayers | Raster/maps services | Complementary use |
| Allmaps | https://github.com/Allmaps/Allmaps | Georeferencing IIIF images | Prototype |
| PostGIS | https://github.com/postgis/postgis | Spatial data | Adopt with PostgreSQL |
| PMTiles | https://github.com/protomaps/PMTiles | Tile packaging | As needed |
| SunCalc | https://github.com/mourner/suncalc | Solar position | Low-cost integration |
| Skyfield | https://github.com/skyfielders/python-skyfield | Astronomy | Specialist microservice |
| DuckDB | https://github.com/duckdb/duckdb | CSV/Parquet querying | Data lab/ingestion |
| Apache Superset | https://github.com/apache/superset | Admin analytics | Optional |
| TanStack Table | https://github.com/TanStack/table | Database browser table | Adopt/validate |
| TanStack Virtual | https://github.com/TanStack/virtual | Huge record lists | Adopt/validate |
| Mirador | https://github.com/ProjectMirador/mirador | IIIF document viewer | Evaluate |
| Universal Viewer | https://github.com/UniversalViewer/universalviewer | IIIF display | Evaluate |
| OpenSearch | https://github.com/opensearch-project/OpenSearch | Full text and facets | Optional at scale |
| Tesseract | https://github.com/tesseract-ocr/tesseract | Printed OCR | Baseline |
| Kraken | https://github.com/mittagessen/kraken | Historical text OCR | Specialist workflow |
| eScriptorium | https://gitlab.com/scripta/escriptorium | Handwriting transcription | Evaluate |
| OpenAI Whisper | https://github.com/openai/whisper | Oral history ASR | Evaluate cost/privacy |
| whisper.cpp | https://github.com/ggml-org/whisper.cpp | Local ASR alternative | Evaluate |
| Discourse | https://github.com/discourse/discourse | Community forums | Independent service candidate |
| Heritrix | https://github.com/internetarchive/heritrix3 | Authorised web preservation | Later |
| Internet Archive BookReader | https://github.com/internetarchive/bookreader | Digitised book viewer | Later |
| Wolfram Alpha API | https://products.wolframalpha.com/api/ | External computation | Optional, not OSS |

**Anti-patterns:** building three genealogy systems in parallel, exposing a public API key in client code, scraping restricted sources as a substitute for licensed connectors, using a sanctions-specific matching tool to infer genealogy without carefully tuned evidence logic, indexing private interviews in a publicly searchable database.

# 14. Updated data model, APIs and integration contracts

## 14.1 Additions to canonical entities

The original blueprint's entities remain. Add:

- `TreeImportJob`, `TreeImportManifest`, `ExternalTreeReference`, `MergeProposal`, `GraphMutationHistory`.
- `PersonNarrative`, `NarrativeParagraphClaim`, `PhotoGallery`, `MediaEntityLink` (with reviewed status).
- `HistoricalConcept`, `ConceptSense`, `InstitutionHistory`, `OccupationHistory`, `JurisdictionPeriod`.
- `ContextObservation`, `ContextDataset`, `ContextComparison`, `SamplingCaveat`.
- `TestimonyDocument`, `InterviewSegment`, `QuestionnaireResponse`, `Speaker`, `MentionCandidate`, `DateOfWriting`, `PeriodDescribed`.
- `HistoricalPlaceAlias`, `HistoricBoundary`, `HistoricalMapLayer`, `GeocodingAssertion`, `JourneyObservation`.
- `SourceCustody`, `SourceDistribution`, `LicenceGrant`, `DatasetAccessPolicy`, `IntegrationVerification`.
- `ContributionUsageEvent`, `DonationLedgerEntry` (if not already present in v1).

## 14.2 Example assertions schema

```ts
interface HistoricalAssertion {
  id: string;
  subjectId: string;
  predicate: string;
  value: unknown;
  validTime?: { start?: string; end?: string; precision?: string };
  placeId?: string;
  evidenceIds: string[];
  status: 'documented' | 'corroborated' | 'reported' | 'contextual' | 'inferred' | 'unresolved';
  createdBy: 'user' | 'import' | 'assistant' | 'partner';
  reviewedByUser: boolean;
  visibility: 'private' | 'project' | 'public';
}

interface ContextObservation {
  id: string;
  datasetId: string;
  measurement: string;
  unit?: string;
  geographicScope: string;
  timeStart?: string;
  timeEnd?: string;
  population?: string;
  kind: 'observed' | 'estimate' | 'modelled' | 'anecdotal';
  evidenceId: string;
  applicabilityNote: string;
}

interface TestimonySegment {
  id: string;
  collectionId: string;
  speakerId?: string;
  transcriptText?: string;
  timestampStartMs?: number;
  timestampEndMs?: number;
  createdAtPeriod?: string;
  describedPeriod?: { start?: string; end?: string };
  rightsPolicyId: string;
  mentions: string[]; // reviewed or tentative entity links
}
```

Dates must support approximate, uncertain, partially known and period-calendar differences. The code sample is illustrative, not a production-ready historical date standard.

## 14.3 Proposed REST surface

```text
POST /api/trees/imports
GET  /api/trees/imports/{id}/manifest
POST /api/trees/imports/{id}/commit
POST /api/trees/imports/{id}/rollback
GET  /api/trees/{id}/health
POST /api/trees/{id}/branch-proposals
POST /api/persons/{id}/merge-proposals
POST /api/persons/merge-proposals/{id}/approve
POST /api/persons/merge-proposals/{id}/undo
GET  /api/persons/{id}/life-story
GET  /api/persons/{id}/gallery
GET  /api/persons/{id}/journeys
POST /api/context/explain-record
GET  /api/context/concepts/search
GET  /api/context/institutions/{id}
POST /api/research/testimony/search
GET  /api/research/testimony/{id}/segments
POST /api/research/testimony/compare
POST /api/research/world-context
GET  /api/maps/layers?year=...
GET  /api/sources/{id}/access-capabilities
```

Implement access control and source rights in the **server-side** execution layer; do not rely on hidden buttons in UI.

## 14.4 Update connector capability manifest

```ts
interface ArchiveHubConnectorCapabilities {
  search: boolean;
  browse: boolean;
  getRecord: boolean;
  getImage: boolean;
  getTranscript: boolean;
  getTimeSegment: boolean;
  getHistoricGeometry: boolean;
  downloadPermitted: boolean;
  canCacheRecord: boolean;
  canRunCommercialAnalysis: boolean;
  authentication: 'none' | 'api_key' | 'oauth' | 'partner' | 'research_approval';
  accessLevel: 'open' | 'registered' | 'paid' | 'restricted' | 'link_only';
  attributionRequired: boolean;
  rateLimitDescription?: string;
  rightsPolicyId: string;
  lastVerified?: string;
}
```

For each endpoint, distinguish connector failure, incomplete search coverage, inaccessible full text and a genuine zero-result response.

# 15. Interface changes for the existing prototype

Do not replace the existing visual style. Extend the chat-centred page and right contextual panel:

## 15.1 Sidebar

Keep Chats, Projects, Files, Homepage, archive/discovery and profile/settings. Add the Research Basket as a contextual or project-level item, not another top-level user area unless usability testing supports it.

## 15.2 Right-hand panel modes

1. `Database` — source list/table/gallery/map and record detail.
2. `Person` — Story | Timeline | Gallery | Tree | Evidence.
3. `Record` — Original | Transcript | Explain | Related records | Citation.
4. `Context` — Occupation | Institution | Comparable testimony | Statistics | Maps.
5. `Map` — historical layer controls, time slider, geocoding confidence, journey traces.
6. `Testimony` — audio/transcript, timestamped passages, named mentions, compare.
7. `Review` — imported branch, duplicate and merge proposal with explicit approval.

Provide collapsible and full-screen views, keyboard navigation, accessible table and image descriptions. Do not force the user to read long AI answers to see a family tree or original scan.

## 15.3 Entry-point prompts

- “Import a family tree and check its connections.”
- “Explain this old certificate, census or workhouse record.”
- “Build the life story of someone in my tree.”
- “Show how this family moved over time.”
- “What did people with this occupation experience in this period?”
- “Browse contemporary diaries and oral histories for this town.”
- “What was happening around this house in 1900?”

## 15.4 Avoid a payment-friction trap

No donation is triggered by scrolling, loading a row or accidentally opening a link. If existing donation functionality is retained, allocate only on explicitly defined qualifying uses; enforce the user's opt-in monthly cap and log source-level payout rights.

# 16. AI orchestration and research-integrity rules

## 16.1 Query routing

Classify requests as:

- `entity_fact`: find primary evidence on named person/place/event.
- `explain_record`: explain term/institution/document purpose.
- `comparative_lived_experience`: retrieve period-matched testimony with caveats.
- `aggregate_context`: query population/wage/weather/economic datasets.
- `genealogy_validation`: compare relatives, dates and relationship claims.
- `geographic_reconstruction`: map and spatial history.
- `source_discovery`: locate a holder, not necessarily the full record.

For a compound question, execute multiple tracks and combine only at the presentation layer, preserving citation types.

## 16.2 Retrieval / evidence constraints

- No unsupported intimate or emotional reconstruction: “she must have felt abandoned” is speculation absent direct testimony.
- Clearly separate *the person said X* from *people in similar circumstances reported X*.
- For a retrospective interview, record both interview date and recalled period; explain memory limitations.
- When the source is an indexed catalogue, say it is a reference to a document, not automatically its content.
- Don't infer child identity from a shared surname, address or census age alone.
- When an archive is inaccessible, offer a source reference and access route; do not fabricate a summary.
- Short quoted excerpts must respect provider rights; link to original or show authorised transcript passages.
- Treat person matches as candidates with reviewable evidence, especially for common names.
- Preserve negatives and ambiguity: “no result from the checked collections” is not “no record exists.”

## 16.3 Data minimisation and consent

Living people's data, private diaries, interviews, mental-health and family disclosures demand stronger access controls, consent and retention policies. No automatic publication or cross-user person resolution. Restrict bulk indexing of research cohort datasets if the conditions disallow reidentification, commercial use or individual linkage.

# 17. Permissions, licensing, privacy and contributor economics

## 17.1 Licensing priority

Set rights per **record and derivative**, not merely per repository or domain. Software licence does not grant access to a third-party archival collection; public scans do not imply a right to republish; metadata and images may carry different terms. Use an explicit licensing register before ingesting datasets at scale.

## 17.2 Fee and donation separation

Maintain separate fields for: user subscription or credits, external licensed access fees, ArchiveHub-funded contributor royalties, optional user micro-donations, and one-off donations. Users set an opt-in donation rate (such as 1p or 5p per qualifying use) and a monthly cap. Settle aggregated contributions rather than processing each penny separately. Charity / Gift Aid status must not be implied for individual or commercial recipients.

## 17.3 Partner proposition

For local histories and volunteer archives, offer hosting, OCR, transcription, place tagging, searchable catalogue, source attribution, controls on public/private content, export and transparent usage reports. Any per-use payment must be contractually eligible, auditable, resistant to abuse and within revenue limits.

# 18. Prioritised implementation programme

This modifies the v1 roadmap by bringing **life-story interpretation and tree integrity forward**, while treating long-tail data acquisitions as progressive additions rather than MVP prerequisites.

## Phase A — Stable evidence-first foundation (P0)

1. Preserve prototype design, chat, projects, files, Archive Explorer.
2. Canonical sources, assertions, provenance, permissions and stable IDs.
3. GEDCOM 5.5.1/7 staging import, import manifest, basic export and missing-media warnings.
4. Person views: minimal Story, Timeline, Gallery, Tree/Evidence.
5. Basic tree-health checks; non-destructive merge preview and undo.
6. Implement one end-to-end `Explain This Record` workflow from an uploaded scan/transcription, distinguishing fact, context and unknowns.
7. Seed source registry with access capability states and verified-at status.

## Phase B — Useful historical and family research (P1)

1. Branch Review and source validation for proposed ancestors.
2. Migration map using sourced residences, locations and temporal uncertainty.
3. Institution/occupation contextual dictionary with a modest curated UK starting set.
4. Two to four rights-compatible external connectors selected on access grounds (e.g., Wikidata, Europeana, Historic England, Gazette, open historical GIS sources).
5. Research Basket, saved citations, comparison views.
6. Media gallery and transcript citation workstream.
7. Pilot on a real GEDCOM and a documented historical institutional record **with permission**.

## Phase C — Lived experience and Historical World Model (P2)

1. Oral-history ingestion for user-created/partner-authorised recordings.
2. Retrospective-vs-contemporary metadata and segment-level citations.
3. Comparable-testimony retrieval, time/place/occupation facets and bias disclosure.
4. Property/neighbourhood explorer; historic maps, planning, heritage and sale data where licensed.
5. Museum object integration and representative imagery.
6. Historical climate and solar calculation demonstrators.
7. Institutional and university archives partner programme.

## Phase D — Breadth, community and commercial partnerships (P3)

1. Historical school, sport, insurance, shipping and specialist government records.
2. Licensed BMD/census image and transcript partnerships; negotiate as commercial product.
3. Authorised society archives, bulk transcriptions and local interview projects.
4. Advanced comparative narratives, books/exhibitions and collaborative research.
5. Expanded contributor royalties, donation dashboards, grant programme and settlements.
6. Further internationalisation, jurisdictions, languages and historical geography.

## 18.1 Build vs integrate decisions

Before work on any large system, write a one-page evaluation: maintainability, licence, operational burden, data interoperability, security, identity model, service architecture, import/export and estimated delivery cost. Keep a single authoritative graph model even when external applications manage specialised records.

# 19. Testing, worked cases and definition of done

## 19.1 Test case: imported family tree

Given GEDCOM with duplicated person, impossible chronology, source-less parent link, disconnected branch and missing photo path, system imports into staging, reports each problem, proposes remediations and does not silently change the source file. After review, user can merge/split and undo without orphaning relationships.

## 19.2 Test case: historical institution in Wiltshire

Given an **actual** record image/transcription identifying an institution, person and period, system explains the literal text, checks institution name/date against archives, distinguishes Old/New Poor Law contexts, builds a research trail and marks motive/experience unknown unless documented. If the institution cannot be identified, system says so.

## 19.3 Test case: life story and migration

Given a person with 1881 and 1891 census residences, system creates timeline and map with two sourced points, labels period between them unknown, and offers historical neighbourhood context without asserting a precise move date or route.

## 19.4 Test case: testimony and sampled context

Given a 1970s interview recalling childhood in 1905, system displays both dates, cites timestamp/paragraph, distinguishes memories from contemporary 1905 evidence and never claims representativeness absent a valid study design.

## 19.5 Test case: external source rights

Given a licensed metadata-only connector, system shows permitted records, refuses unauthorised image/full-text ingestion, links to owner and applies no incorrect royalty or user charge.

## 19.6 Test case: sun/shadow photo analysis

Given approximate photo location and candidate date, system calculates a range of solar angles, discloses orientation/date uncertainty and does not manufacture an exact timestamp.

### Release acceptance criteria

- [ ] At least one end-to-end person story cites underlying imported or linked evidence.
- [ ] Record explanations have separate “document says / historical context / uncertainty” sections.
- [ ] Tree import manifest accurately reports count, warnings and unresolvable media.
- [ ] Merge preview and undo are tested against graph integrity.
- [ ] Family migration map labels documented points and uncertain routes correctly.
- [ ] One diary/interview passage retains authorship, writing date, recalled date and rights metadata.
- [ ] At least two genuine external connectors are functional under their verified terms.
- [ ] Source directory marks link-only and restricted research collections accurately.
- [ ] No uploaded material becomes public without approval.
- [ ] All downloadable exports carry provenance and record-level rights labels.

# 20. Outreach, due diligence and unresolved decisions

## 20.1 Priority institutional enquiries

1. **Free UK Genealogy:** scope and eligibility for bulk extracts; potential partnership, attribution, community payments.
2. **FamilySearch developer programme:** approved API access, Family Tree records vs historical-record search, and commercial product requirements.
3. **GRO / original custodians:** authorised indexes, paid-image workflows and commercial reuse possibilities.
4. **UK Data Service:** historical census research access (I-CeM), commercial restrictions, aggregate contextual research.
5. **Mass Observation / University of Sussex:** metadata, permitted excerpts, potential partner indexing, researcher access.
6. **Great Diary Project / Bishopsgate:** catalogue, digitisation pilot and participant/publication rights.
7. **British Library National Life Stories / local oral-history groups:** transcripts, searchable metadata and access arrangements.
8. **Jisc Archives Hub / regional archives:** discovery interoperability and OAI-PMH/IIIF availability.
9. **Local history societies in Berkshire:** pilot datasets and record explanations, oral-history project design.
10. **NLS / Historic England / relevant geospatial providers:** commercial map services and attribution/licensing.

## 20.2 Open product decisions

- Is Gramps Web API the genealogical subsystem, or should ArchiveHub implement its own family record model and use Gramps only for import/export? **Decide with a spike.**
- Will users be able to publish or monetize imported family-tree content from third parties? **Require permissions per source.**
- Which v1 connector has both a stable API and commercial rights compatible with the intended service? **Verify before committing.**
- Which provider will handle optional payments and whether donations to volunteer groups can be handled as charitable transfers? **Seek payment/legal advice.**
- What minimum historical precision is needed for address matching before showing house-level pins?
- What consent/embargo controls will protect new oral-history participants?
- Which qualitative datasets can legally be indexed and analysed in a commercial application?
- Will there be citation-backed public “concept explainers” contributed by partner historians and reviewed by editors?
- Which features become credit-using AI actions and which remain free manual browsing?

## 20.3 Source verification checklist

For any chosen source: check official landing page, developer docs, API registration, current terms, rate limits, rights and sublicensing, bulk metadata/images, attribution, privacy/PII, removal requests, dates of coverage, update cadence and whether an actual implementation test succeeds. Log date and version. This addendum does not substitute for those checks.

# 21. Suggested VS Code implementation prompt

```text
You are extending an existing ArchiveHub chat-first historical research prototype.
Read these two specifications in order:
1. docs/ARCHIVEHUB_MASTER_BLUEPRINT.md (v1.0)
2. docs/ARCHIVEHUB_ADDENDUM_V3_2026-11-10.md (consolidated v3 addendum, including §§23–31)

Preserve the four product areas (Record, Research, Home, Connect), Archive Explorer,
existing UI and project/files structure. Do not rebuild the design unless needed to
implement a described workflow. Never treat example data as real records.

First inspect the repository and report the actual implemented vs simulated features.
Then propose a short architecture decision memo for GEDCOM engine, provenance model,
person-centric views and connector capabilities.

Implement an incremental vertical slice:
- import a small GEDCOM test file into private staging;
- generate an import manifest with count, citation and missing-media warnings;
- display a person with Story, Timeline, Gallery and Tree/Evidence tabs;
- provide an 'Explain this record' panel whose output explicitly separates literal
  document evidence, sourced historical context and unresolved questions;
- render sourced residence events on a map without inventing travel paths;
- preserve source IDs, rights and user-approved changes.

Add unit and integration tests for tree consistency, source provenance, uncertainty,
privacy and import/export behaviour. Do not call restricted APIs or scrape sites
without authorised access. Keep secrets server-side. If a spec item is missing data
or credentials, provide a realistic mock adapter marked as mock plus a precise TODO.
Work in small commits, reporting every architectural choice and any deviation.
```

# 22. Source links and documentation index
23. Cultural History Engine: purpose, evidence rules and entity model
24. Cultural discovery: art, literature, folklore, music and media
25. Expanded cultural sources, APIs and datasets
26. Recently identified GitHub repositories: inventory and adoption assessment
27. Illustrated Historical Report generator: product and technical requirements
28. UI extensions, source rights, micropayments and moderation
29. Phased cultural build, acceptance tests and demonstration scenarios
30. VS Code implementation prompt for the cultural extension
31. Additional cultural documentation and links

This is a developer reference list, **not a claim that each resource is currently accessible to ArchiveHub**. The source inventory in §12 provides routes and caveats. Official provider documentation is preferred over third-party descriptions.

### Standards, core software and interoperability

- FamilySearch GEDCOM: <https://github.com/FamilySearch/GEDCOM>
- GEDCOM standards hub: <https://gedcom.io/>
- Gramps Web API: <https://github.com/gramps-project/gramps-web-api>
- IIIF Consortium: <https://iiif.io/>
- OAI-PMH specification: <https://www.openarchives.org/pmh/>
- NLS historical mapping: <https://maps.nls.uk/>
- Historic England data: <https://historicengland.org.uk/listing/the-list/data-downloads/>
- SunCalc: <https://github.com/mourner/suncalc>
- UK Government API catalogue: <https://www.api.gov.uk/>

### Genealogical and named historical records

- GRO: <https://www.gro.gov.uk/>
- Free UK Genealogy: <https://www.freeukgenealogy.org.uk/>
- FreeBMD: <https://www.freebmd.org.uk/>
- FreeREG: <https://www.freereg.org.uk/>
- FreeCEN: <https://www.freecen.org.uk/>
- FamilySearch developer hub: <https://developers.familysearch.org/>
- National Archives Discovery: <https://discovery.nationalarchives.gov.uk/>
- UK Data Service: <https://ukdataservice.ac.uk/>
- CWGC: <https://www.cwgc.org/>
- The Gazette: <https://www.thegazette.co.uk/>

### Social history, testimonies, context

- Mass Observation: <https://www.massobs.org.uk/>
- Great Diary Project: <https://thegreatdiaryproject.co.uk/>
- East Midlands Oral History Archive: <https://le.ac.uk/emoha/catalogue>
- London Lives: <https://www.londonlives.org/>
- Digital Panopticon: <https://www.digitalpanopticon.org/>
- Reading Experience Database: <https://www.open.ac.uk/Arts/reading/UK/>
- Victoria County History: <https://www.history.ac.uk/research/victoria-county-history>
- British History Online: <https://www.british-history.ac.uk/>
- Cambridge occupations research: <https://www.campop.geog.cam.ac.uk/research/occupations/datasets/>

### Economy, maps, environmental and cultural data

- Bank of England research datasets: <https://www.bankofengland.co.uk/statistics/research-datasets>
- Land Registry price paid: <https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads>
- Planning Data England: <https://www.planning.data.gov.uk/>
- UK PlanIt: <https://www.planit.org.uk/>
- Met Office HadUK-Grid: <https://www.metoffice.gov.uk/research/climate/maps-and-data/data/haduk-grid>
- Europeana APIs: <https://api.europeana.eu/>
- UK Museum Data Service: <https://museumdata.uk/using-data/our-apis/>
- V&A: <https://developers.vam.ac.uk/>
- Met Museum: <https://metmuseum.github.io/>
- Art Institute of Chicago: <https://api.artic.edu/docs/>
- Open Library: <https://openlibrary.org/developers/api>
- Wolfram Alpha API: <https://products.wolframalpha.com/api/>

---

## Original v2 implementation principle (retained)

**ArchiveHub should not merely accumulate records; it should make evidence understandable without losing the distinctions that make it trustworthy.** Start with one real person, one GEDCOM import, one historical document, one explanatory context source and one map. Prove that the same source is represented accurately in the tree, biography, gallery, document viewer, contextual explanation and research basket. Then expand the catalogue and data network in measured, rights-aware stages.

---

# 23. Cultural History Engine: purpose, evidence rules and entity model

## 23.1 Product rationale

**New addition after v2:** ArchiveHub should connect historical people, families, places, institutions, occupations, events and ways of life to **artistic, literary, musical, folkloric, cinematic, theatrical and photographic representations**. These links are intended both for exploratory browsing and the generation of evidence-led, beautifully illustrated historical reports.

The addition does **not** introduce a fifth top-level user area. It is a shared **Cultural History Engine** serving **Record** (person and family pages, life stories), **Research** (Archive Explorer, cultural discovery and comparisons), **Home** (articles, exhibitions, published books) and **Connect** (scholar/collector contributions and community curation).

The fundamental distinction is between:

1. **Documentary evidence** — a record that establishes or supports a historical assertion about a specific person, place or event.
2. **Contemporary context** — historically dated information about conditions faced by people in an identifiable population, region or period.
3. **Contemporary cultural representation** — art or writing from the period that represents or responds to a relevant social world, sometimes imaginatively or selectively.
4. **Retrospective cultural representation** — later interpretations of an earlier period (historical novels, period films, modern retellings).
5. **Direct representation of the subject** — an identifiable portrait, building depiction, recorded song about an identifiable event/person, or work set at the particular location. Only claim this connection when the source actually supports it.

A painting of peasant labour in France in 1857 can illuminate a similar occupation in England without providing direct evidence of an English ancestor's circumstances. A fictional film set in Victorian Oxford and shot elsewhere is not a photographic record of Victorian Oxford. A ballad documented in 1900 may have earlier origins, but the collection date is not the composition date. The software and generated reports must preserve these distinctions visibly.

## 23.2 Use cases

- **Ancestral livelihood:** “Show paintings, songs, contemporary descriptions and literature relevant to a Berkshire agricultural labourer, c.1845–1890.”
- **Geographic cultural history:** “What works of art, poems and travel accounts depict Oxford between 1750 and 1850?”
- **Institutional lived experience:** “Add period descriptions of workhouses and poor relief to the brothers' Wiltshire family history, with caveats about comparability.”
- **Interactive discovery:** “Open a gallery of relevant visual depictions; cycle through paintings in the side panel and save three to my project.”
- **Integrated long report:** “Write a sourced, illustrated account of this family member's life including maps, photographs, songs and contemporary literature.”
- **Community curation:** A local historian supplies a verified reference to a painter's view of a village; their collection is credited and connected to ArchiveHub's existing optional contribution system.

## 23.3 New or extended data types

Add these to the existing person/place/event/source/claim/collection model in §§4–16, with typed relationships rather than free-text links:

| Entity | Required properties | Optional/extended properties |
|---|---|---|
| `CulturalWork` | stable ID, title, work type, source catalogue, source URL, provenance status | creation date range, represented date range, creators, language, original title, edition/manifestation, genre, medium, culture |
| `CulturalManifestation` | work ID, manifestation identifier, provider, access policy | edition, translation, recording, scan, specific print, IIIF manifest, duration, format, DOI/ISBN/ISRC/catalogue number |
| `CulturalSubject` | concept ID, controlled term, classification source | occupation, practice, institution, social class, object, event, narrative theme, place |
| `DepictedPlace` | place ID, association type, evidence | geocoordinates or region, viewing position, geographic precision, depiction certainty |
| `CulturalRelation` | work ID, linked entity, relation type, provenance, confidence class | evidence passage, source paragraph/page, creator rationale, human reviewer |
| `CulturalExcerpt` | manifestation ID, anchored location, quotation rights | short quote, source page, line, chapter, timestamp, OCR confidence |
| `MediaAsset` | exact asset origin, rights/attribution fields, access permissions | image dimensions, IIIF, thumbnail, transcript, captions, duration, rights territory |
| `Report` | report ID, project ID, owner, draft state, source manifest | template, selected sections, layout, export formats, approval history |
| `ReportBlock` | report ID, block type, content, citations | media placement, evidence claims, cultural relation rationale, layout controls |

Maintain separate dates for creation, publication, period depicted, performance, collection/field-recording, transcription and cataloguing. Use open intervals and uncertain dates where necessary. Store distinct original works, editions/translations, recordings and scans; a public-domain poem and a copyrighted recent recording of it are not the same asset.

### Suggested typed relations

`depicts_place`, `created_in_place`, `creator_lived_in_place`, `set_in_place`, `mentions_place`, `documents_person`, `portrays_occupation`, `responds_to_event`, `illustrates_practice`, `associated_with_period`, `collected_in_place`, `recorded_at_date`, `later_interpretation_of`, `contradicts_stereotype`, `cited_in_report`.

Every automated relationship should have a generated proposal status and supporting evidence. Do not convert vector similarity, appearance-based speculation or a shared surname into a verified relation.

## 23.4 Matching/ranking logic

Implement a deterministic, inspectable baseline ranking system before more ambitious semantic inference. Proposed dimensions: exact subject/entity match, geographical distance and level of place match, creation-date overlap, depicted-period overlap, medium requested by user, specificity of occupational/social theme, quality of catalogue metadata, source trust and display/reproduction eligibility. Represent the match rationale in human-readable form; do **not** expose a single apparently objective “historical authenticity score.”

Suggested result fields:

```json
{
  "work_id": "provider:catalogue-item",
  "title": "Example artwork",
  "representation_type": "contemporary_comparative",
  "relation": "portrays_occupation",
  "related_entity_id": "occupation:agricultural_labour",
  "place_match": "different_region_same_country",
  "creation_date": "1850/1860",
  "depicted_period": "nineteenth_century",
  "reason": "Depicts field labour of the period; not evidence of the ancestor's actions",
  "source_ref": "original-provider-record-url",
  "media_permission": "metadata_only",
  "verification": "requires_review"
}
```

Fields above are an example contract, not live source data. Work rights, asset rights and excerpt rights must be evaluated separately.

# 24. Cultural discovery: art, literature, folklore, music and media

## 24.1 Art, illustrations, prints and ephemera

A cultural gallery can be opened from a person, place, occupation, event, building or period in the existing side panel. Filter by **subject, date, geography, artistic medium, creator, repository, copyright/reuse status and representation type**. Offer list/grid/map/timeline views, compare mode, next/previous, collect to Research Basket, and “why am I seeing this?” explanations. Permit users to remove/reorder suggestions and manually add catalogue URLs.

Examples: Constable's *The Hay Wain* as an English pastoral representation; Millet's *The Gleaners* as a French comparison of agricultural labour; William Turner of Oxford's landscapes as location-related artworks. Do not assume a painting has precise geo-coordinates unless catalogued or separately documented. Combine with IIIF, Mirador, Universal Viewer and Annotorious for zoom, comparison and annotations where permitted.

A future **Art on the Map** layer should distinguish depiction point, artist's working location, present collection location, fictional setting and inferred camera/viewpoint. These are not interchangeable. Date filters should distinguish **date work created** from **date scene depicts**.

## 24.2 Literature, poetry and literary geography

Support full-text discovery only for duly licensed or public-domain (in the relevant jurisdiction) texts. Searching must retrieve passage anchors and bibliographic identity: work, author, edition or translation, chapter/page/line where available, and source link. Index person and place names, material objects, trades, institutions, dialect, customs, work, food, religion, domestic life and social conditions. The user may specify a creator such as Blake, Byron, Milton, Hardy, a literary period or a location such as Oxford.

`LiteraryGeography` distinguishes: `set_in`, `written_in`, `author_resided_in`, `mentions`, `depicts`, `fictionalized_from` and `recorded_visit`. Reconcile historical spellings of place names via existing gazetteer and map services. A passage describing a fictional scene is contextual material, **not** testimony about an actual ancestor.

Avoid long copyrighted excerpts. For modern copyrighted works, metadata and links may be available even when the actual passage cannot be included in an exported report. Editions and translations can have independent rights even when the underlying original is public domain.

## 24.3 Ballads, folk songs, nursery rhymes and folklore

Add a `FolkloreVariant` and `SongVariant` model: canonical/song-family identifier (e.g. Roud number where legitimately available), title variants, collected place, collector, singer/informant where consent and sensitivity permit, recording date, publication date, claimed historical origin, transcription/lyrics, tune/score, source, language/dialect and rights by asset. Treat traditional song variants as evidence of **a documented version** rather than evidence that everyone in the region knew the song.

Start with metadata and reference links from **Vaughan Williams Memorial Library / Roud indexes**, **Bodleian Broadside Ballads**, **Traditional Ballad Index**, **Tobar an Dualchais**, **Irish Traditional Music Archive**, and **Folklore Society**. Verify each provider's bulk data and commercial terms individually. Distinguish a public-domain traditional composition from protected recordings, arrangements and new critical editions.

Provide a folklore panel for customs, games, children's rhymes, festivals, beliefs and superstitions, with date/place/collector and historiographical cautions. Do not repackage speculative nursery-rhyme origin stories as fact.

## 24.4 Film, theatre, broadcasting and photography

Support historical footage and representations via BFI, BBC Archive, British Pathé, IWM, Europeana and specialist regional archives, subject to permitted metadata, embedding and licensing. Use separate relations `filmed_at`, `depicts_actual_place`, `fictionally_set_in`, `reconstructed_period`, `aired_on`, `recording_of_performance`. Add timecoded playback only where host allows it. Default to linking out for restricted footage.

A cultural report can include a film still or thumbnail only if the relevant asset permission permits; otherwise show a text card and external link. Recognise the difference between a 1950 documentary and a 1990 drama depicting 1950.

## 24.5 Context quality controls

- Show **contemporaneous / near-contemporary / retrospective** labels.
- Separate **literal evidence, general historical context, and illustrative cultural representation** visually in every person profile and report.
- Prefer local/regionally relevant examples over famous but geographically unrelated art; permit comparative works with explicit labels.
- Make every cross-collection item openable in Archive Explorer with source provenance.
- Preserve period terminology, modern terminology and explanation separately; avoid presenting obsolete derogatory categories without context.
- When no permitted image exists, retain a useful metadata-only cultural reference rather than silently substituting unrelated imagery.

# 25. Expanded cultural sources, APIs and datasets

**Registry status convention:** `API` = documented API candidate; `DUMP` = bulk metadata/data candidate; `CATALOGUE` = browse/search and source-link candidate; `PARTNER` = likely requires institutional agreement or licensing; `TOOL` = software used in a local processing pipeline. These are proposed routes, not endorsements or guarantees of present access. Check terms and endpoint behaviour before implementation.

## 25.1 Artworks, collections, images, manuscripts and cultural objects

| Source | URL | Route | Intended functionality / caution |
|---|---|---|---|
| Metropolitan Museum Open Access | https://github.com/metmuseum/openaccess | DUMP | Artwork metadata; check each image/asset independently |
| Tate Collection snapshot | https://github.com/tategallery/collection | DUMP | British artwork/artist metadata; known historical snapshot; not current complete collection/images |
| MoMA Collection | https://github.com/MuseumofModernArt/collection | DUMP | Modern art metadata; image rights separate |
| Cleveland Museum of Art | https://openaccess-api.clevelandart.org/ | API/DUMP | Search artwork and reusable images subject to item flags |
| Art Institute of Chicago | https://api.artic.edu/docs/ | API/DUMP | Search, thumbnails, image metadata; follow provider asset policies |
| The Met Museum API | https://metmuseum.github.io/ | API | Artwork records and eligible images |
| V&A Collection API | https://developers.vam.ac.uk/ | API | Historical design, clothes, household objects, prints, illustrations |
| Rijksmuseum data | https://data.rijksmuseum.nl/ | API/CATALOGUE | Dutch/European art; distinguish object metadata from image rights |
| National Gallery of Art (US) | https://www.nga.gov/open-access-policy | DUMP/CATALOGUE | Open images and artwork metadata where indicated |
| Europeana | https://api.europeana.eu/ | API | Federated object discovery; rights vary by providing institution |
| Digital Public Library of America | https://pro.dp.la/developers | API/DUMP | Cross-institution US cultural metadata |
| Wikimedia Commons | https://commons.wikimedia.org/ | API | Media and structured descriptions; verify each licence and attribution |
| Art UK | https://artuk.org/ | CATALOGUE/PARTNER | UK-localised artworks; licences needed for many reproductions |
| British Museum collections | https://www.britishmuseum.org/collection | CATALOGUE | Prints, drawings, historical artefacts and objects |
| Tate online | https://www.tate.org.uk/art | CATALOGUE | British and modern art discovery |
| National Gallery London | https://www.nationalgallery.org.uk/paintings | CATALOGUE | Historical paintings and collection links |
| Ashmolean | https://www.ashmolean.org/collections | CATALOGUE | Oxford-related artworks and objects |
| Digital Bodleian | https://digital.bodleian.ox.ac.uk/ | CATALOGUE/IIIF | Books, images, manuscripts, prints, ballads, maps |
| London Picture Archive | https://www.londonpicturearchive.org.uk/ | CATALOGUE | Historical views of streets and buildings |
| National Galleries of Scotland | https://www.nationalgalleries.org/ | CATALOGUE | Portraits and historical Scottish art |
| UK Museum Data Service | https://museumdata.uk/using-data/our-apis/ | API | UK objects/museums; API registration/terms as applicable |
| Smithsonian Open Access | https://www.si.edu/openaccess | API/DUMP | Historical material culture, objects, scientific collections |
| GLAM Workbench | https://github.com/GLAM-Workbench | TOOL | Working examples harvesting cultural and newspaper sources |

## 25.2 Literature, text corpora and bibliographies

| Source | URL | Route | Notes |
|---|---|---|---|
| Project Gutenberg | https://www.gutenberg.org/ | DUMP/CATALOGUE | Full text if permitted in UK commercial context; US rights not sufficient |
| Gutendex | https://github.com/garethbjohnson/gutendex | API/TOOL | Self-hostable Gutenberg catalogue API |
| Standard Ebooks | https://github.com/standardebooks | DUMP/TOOL | Individual edition repositories, rights assessment per work/edition |
| Standard Ebooks toolchain | https://github.com/standardebooks/tools | TOOL | EPUB editing/validation/production |
| Wikisource | https://en.wikisource.org/ | API | Historical text and transcriptions; inspect per-page licence |
| Open Library | https://openlibrary.org/developers/api | API | Bibliographic discovery; no presumption of full text rights |
| HathiTrust | https://www.hathitrust.org/ | CATALOGUE/PARTNER | Bibliographic/search/research access under restrictions |
| Google Books | https://developers.google.com/books/docs/v1/using | API | Discovery and previews rather than unrestricted indexing |
| British Library | https://www.bl.uk/ | CATALOGUE/PARTNER | Literary manuscripts, printed texts and archival descriptions |
| Poetry Foundation | https://www.poetryfoundation.org/ | CATALOGUE | Metadata/discovery; do not bulk ingest poems without permission |
| Poetry Archive | https://poetryarchive.org/ | CATALOGUE/PARTNER | Poetry recordings; rights and embedding separately |
| Oxford English Dictionary | https://www.oed.com/ | PARTNER | Historic word meanings; subscription/licensing |
| Open University Reading Experience DB | https://www.open.ac.uk/Arts/reading/UK/ | CATALOGUE | Structured evidence of readers, works and reading practices |

## 25.3 Folk cultures, traditional music, performance and broadcasting

| Source | URL | Route | Notes |
|---|---|---|---|
| VWML and Roud Index | https://www.vwml.org/ | CATALOGUE/PARTNER | Song families, variants, collector data, subject index |
| Traditional Ballad Index | https://balladindex.org/ | CATALOGUE | Scholarly song index; verify downloadable-data reuse |
| Bodleian Broadside Ballads | https://digital.bodleian.ox.ac.uk/ | CATALOGUE/DUMP | Song/ballad images, metadata, linked data where explicitly offered |
| English Folk Dance and Song Society | https://www.efdss.org/ | CATALOGUE/PARTNER | The Full English and related collections |
| Tobar an Dualchais | https://www.tobarandualchais.co.uk/ | CATALOGUE/PARTNER | Scottish traditional audio and oral testimony |
| Irish Traditional Music Archive | https://www.itma.ie/ | CATALOGUE/PARTNER | Music recordings, songs, manuscripts, metadata |
| Folklore Society | https://folklore-society.com/ | CATALOGUE | Folklore literature, custom and childlore discovery |
| BFI archive | https://www.bfi.org.uk/bfi-national-archive | CATALOGUE/PARTNER | Film and TV archival holdings |
| BFI Player | https://player.bfi.org.uk/ | CATALOGUE | Links to legally available films |
| British Pathé | https://www.britishpathe.com/ | CATALOGUE/PARTNER | Historical newsreels and licensed material |
| BBC Archive | https://www.bbc.co.uk/archive | CATALOGUE/PARTNER | Historical broadcasting |
| IWM collections | https://www.iwm.org.uk/collections | CATALOGUE/PARTNER | Wartime visual/audio testimony |
| V&A Theatre and Performance | https://www.vam.ac.uk/collections/theatre-performance | CATALOGUE | Costume, theatre and performance history |

## 25.4 Metadata normalisation and identifier strategy

Use original provider catalogue identifiers and link to Wikidata QIDs where independently reconciled, plus VIAF/ISNI for people/creators, Wikidata or other stable concept IDs for subjects, Roud IDs for folk-song family where available, ISBN/DOI for editions, IIIF manifests for media, GeoNames/WHG/local archival IDs for places. No canonical provider identifier should be inferred from a near-match. Model provenance and source-specific rights at **work, manifestation, asset and excerpt** level.

# 26. Recently identified GitHub repositories: inventory and adoption assessment

This section is the consolidated inventory of **new repositories surfaced in the cultural-history/reports discussions after v2**. Earlier baseline repositories remain in §§12–13 and 22. Entries do not imply they have been installed, security-reviewed, tested or licensed for use; record actual repository commit, licence and maintenance status during adoption. Some links point to GitHub organisations or dataset catalogues rather than deployable services. **Avoid assuming all software is compatible with the current ArchiveHub stack.**

## 26.1 Downloadable artwork datasets and research directories

| Repo | Type | Intended use | Caveat |
|---|---|---|---|
| https://github.com/metmuseum/openaccess | Data | Bulk Met artwork metadata | Art asset rights distinct |
| https://github.com/tategallery/collection | Data/snapshot | British artwork and creator metadata | Historical snapshot; imagery not included |
| https://github.com/MuseumofModernArt/collection | Data | Modern artwork/artist metadata | Image rights separate |
| https://github.com/ClevelandMuseumArt/openaccess | Data/organisation | Cleveland art metadata and eligible assets | Verify exact maintained data location/API |
| https://github.com/art-institute-of-chicago/api-data | Data | Locally indexable museum dataset | Confirm version and licensing |
| https://github.com/georgeblck/art-datasets | Curated index | Identify further art corpora and iconography datasets | Not itself one uniform dataset |
| https://github.com/GLAM-Workbench/digitalnz | Research notebooks | Federated heritage discovery and exploratory browsing | Example patterns, not turnkey backend |
| https://github.com/GLAM-Workbench | Organisation | Cultural heritage data acquisition experiments | Review each notebook's assumptions |

## 26.2 Literary parsing, historical-language and public-domain publication

| Repo | Type | Intended use | Caveat |
|---|---|---|---|
| https://github.com/booknlp/booknlp | NLP | Characters, quotations, place/person mention extraction from novels | Fictional characters ≠ real entities |
| https://github.com/cltk/cltk | NLP | Ancient/pre-modern language pipelines | Language/period-specific accuracy |
| https://github.com/stanfordnlp/stanza | NLP | Multilingual NER, sentence segmentation, linguistic analysis | Historical domain drift; human review |
| https://github.com/standardebooks | Edition repository organisation | Source editions of literary works | Per-edition rights and provenance |
| https://github.com/standardebooks/tools | Publishing tools | EPUB tooling and validation | Evaluate pipeline complexity |
| https://github.com/garethbjohnson/gutendex | Catalogue API | Gutenberg title/author/subject discovery | Metadata vs full text separation |
| https://github.com/GLAM-Workbench/trove-newspapers | Research notebooks | Historical newspaper search/text analysis examples | Australian source; source-specific rules |
| https://github.com/GLAM-Workbench/trove-newspaper-harvester | Harvester | Newspaper metadata/text/image pipeline reference | Respect limits and rights |

## 26.3 Folk-song research and music notation

| Repo | Type | Intended use | Caveat |
|---|---|---|---|
| https://github.com/cuthbertLab/music21 | Music software | Symbolic score analysis, tune/variant comparisons | Scores/recordings licensed separately |
| https://github.com/humdrum-tools/humdrum-data | Music data | Structured musical corpora | Not necessarily historical British folk data |
| https://github.com/humdrum-tools/verovio-humdrum-viewer | Viewer | Interactive notation/score rendering | Browser embedding/security review |
| https://github.com/humdrum-tools/humdrum-documentation | Reference | Music formats, notation tooling and reference workflows | Documentation, not database |

## 26.4 Cultural annotation, place reconciliation and text curation

| Repo | Type | Intended use | Caveat |
|---|---|---|---|
| https://github.com/docuracy/Locolligo | Geodata tooling | Link/geolocate heritage collection metadata | Confirm maintenance and suitability |
| https://github.com/inception-project/inception | Text annotation | Human-assisted semantic annotation and corpus curation | Heavy system; evaluate as separate service |
| https://github.com/annotorious/annotorious | Image annotation | Annotate people/objects/buildings in paintings or photos | Source rights, personal data, user validation |
| https://github.com/dpla/dpla-frontend | Interface reference | Federation discovery/search UI inspiration | Do not assume backend included |
| https://github.com/wikimedia/mediawiki | Platform source | Understand Wikisource/mediawiki integrations | Usually prefer APIs to embedding full CMS |
| https://github.com/OpenRefine/OpenRefine | Previously known; reaffirmed | Name/place/creator reconciliation | Human-in-the-loop matching |
| https://github.com/ProjectMirador/mirador | Previously known; reaffirmed | IIIF side-by-side manuscript viewer | IIIF support depends on provider |
| https://github.com/UniversalViewer/universalviewer | Previously known; reaffirmed | Embedded interoperable viewers | Respect underlying collection rights |

## 26.5 Long-form publishing, references, output formats

| Repo | Type | Intended use | Caveat |
|---|---|---|---|
| https://github.com/quarto-dev/quarto-cli | Publishing | HTML/PDF/Word/book output and research charts | Server-side execution sandboxing |
| https://github.com/jgm/pandoc | Converter | Markdown/document AST and multi-format export | Validate media/citation fidelity |
| https://github.com/typst/typst | Typesetting | Print-quality illustrated volumes | Template engineering; no default Word export guarantee |
| https://github.com/citation-js/citation-js | Citation tool | CSL-style citation parsing/output | Preserve original source locators |
| https://github.com/zotero/translation-server | Metadata extraction | Capture bibliographic metadata and citations | Source site support and licensing |
| https://github.com/standardebooks/tools | EPUB tools | Long-form e-book export | Same repo as literary tooling; list once in dependencies |
| https://github.com/opensearch-project/OpenSearch | Previously known; reaffirmed | Search across text + metadata | Index rights must be checked |

### Potentially incorrect, moved, abandoned or ambiguous repository URLs

Repository names and links surfaced during exploratory conversations are **candidates**, not current verification. Before implementing, run `git ls-remote` (or use GitHub API) for each candidate and check: redirects, actual owner, last release/commit, repository licence, dependencies, installation instructions, sample datasets, commercial use and security notices. In particular, distinguish project web/API URLs from repo URLs; an organisation homepage or umbrella repo should not be treated as a pip/npm package. If a link no longer resolves, preserve the idea in the source registry with `status: needs_replacement` instead of silently fabricating an alternative.

## 26.6 Evaluation rubric and example `source-registry` entry

For each project evaluate integration depth (`dataset | package | separate service | conceptual reference`), maturity, current activity, licence (including copyleft network obligations), expected storage, operating cost, maintenance/security, GDPR/privacy, bulk/asset rights and reliability of the exact extracted features. A zero-purchase-cost project is not necessarily zero operating cost.

```yaml
id: cultural-met-openaccess
kind: bulk_dataset
provider: Metropolitan Museum of Art
repository: https://github.com/metmuseum/openaccess
purpose: museum_cultural_work_discovery
status: candidate_unverified_for_current_deployment
commercial_rights: verify_metadata_and_individual_asset_rights
sync_strategy: scheduled_with_diff_and_provenance
indexes: [creator, title, period, medium, subject, provenance]
media: conditional_per_asset
```

# 27. Illustrated Historical Report generator: product and technical requirements

## 27.1 Entry points and report types

Add **Generate Historical Report** / **Write Illustrated Life Story** affordances from person profiles, family branches, place pages, institutions, topical Research projects and Archive Explorer results. Expose the same workflow through chat: “Write a detailed illustrated report about X” should prepare a report plan, source manifest and preview without publishing or charging for optional third-party content unexpectedly.

Templates:

- **Illustrated life story:** clear chronological story with family, work, migration, relationships, historical surroundings and relevant cultural material.
- **Academic research report:** evidence hierarchy, claim/source matrix, uncertain identifications, notes, references and methodology.
- **Family history book chapter:** polished narrative, photos, heritage maps, captions, sidebars and appendix.
- **Place or cultural history essay:** historic maps, changes over time, artistic/literary representations, voices of residents and thematic bibliography.
- **Institution/occupation profile:** historical meaning, chronology, daily life, contemporary artefacts, testimony, cultural depictions.

Controls: short/detailed/extended length; research period and geography; selection of painting/illustration, literary passages, folklore, songs, audio, maps, photography, economic data and oral histories; publication voice; image density; bibliography format; permitted export channels. Default to contextual quality, not sheer number of illustrations.

## 27.2 Proposed processing stages

1. **Scope:** Establish subject and relevant known person/place IDs, selected family branch, date window and project privacy context.
2. **Evidence snapshot:** Collect permitted primary records, imported GEDCOM assertions, user documents, citations and current confidence/contradiction state; preserve version IDs.
3. **Context retrieval:** Query Historical Context Engine, Historical World Model, Lived Experience Archive, gazetteers and maps with appropriately bounded date/region/subject.
4. **Cultural candidate discovery:** Query approved artwork/literature/song/media connectors, distinguishing full-text from metadata only. Return scored matches with reasons, licences and original catalogue IDs.
5. **Research plan:** Produce an outline and evidence/cultural shortlist; mark specific unknowns and gaps. For expensive external operations or rights purchases, disclose and obtain explicit approval.
6. **Draft:** Generate structured blocks (headings, evidence text, cultural sidebar, image card, map, timeline, quotation, caption, footnote, bibliography, open-question box), not undifferentiated Markdown.
7. **Validate:** Check every concrete event assertion against linked evidence; separate contextual and symbolic representations; validate temporal plausibility, quotations and exact citations; reject fabricated images/passages.
8. **Rights check:** Decide per manifestation and asset whether it may appear in interactive HTML and downloadable PDF/Word/EPUB and in which territory; replace disallowed embeds with catalogue links.
9. **Preview/edit:** Allow rearrangement, replacement, removal, manual annotation and approval. Save drafts privately by default.
10. **Render/export:** Start with live responsive HTML; then PDF and DOCX (and optional EPUB/print book) using appropriate server-side tools. Produce a source manifest and report version.

## 27.3 Suggested report structure

```text
Historical Report
├── Cover: subject, life dates or period, place, provenance note
├── Research summary and caveats
├── The documented life (evidence-linked chronology)
├── Family and relationships (with uncertainty)
├── Work and material conditions
├── Homes, places, movement and historical maps
├── Contemporary cultural depictions (art, prints, objects)
├── Literature and period language
├── Songs, folklore and customary practices
├── Later representations and historiography (clearly distinct)
├── Contemporary voices, diaries and oral histories
├── Outstanding research questions
├── Sources and bibliography
└── Rights/attribution appendix and dataset access notes
```

Every section is optional and evidence-dependent. Do not pad a weakly sourced biography with unsupported scenes or speculative interiors. Use a visible `Nothing suitable found` state where appropriate.

## 27.4 Core API sketch

```http
POST /v1/reports/plan
POST /v1/reports/{id}/search-cultural-candidates
POST /v1/reports/{id}/draft
GET  /v1/reports/{id}
PATCH /v1/reports/{id}/blocks/{blockId}
POST /v1/reports/{id}/validate
POST /v1/reports/{id}/render
POST /v1/reports/{id}/publish
GET  /v1/reports/{id}/source-manifest

GET  /v1/cultural/search?person_id=&place_id=&year_start=&year_end=&media_type=
GET  /v1/cultural/works/{workId}
GET  /v1/cultural/works/{workId}/related
POST /v1/cultural/relations/propose
POST /v1/cultural/relations/{id}/review
```

Design these as conceptual contracts. Match route conventions and authentication to the existing repository. Publishing or spending credits requires explicit approval; report planning/preview never publishes automatically.

## 27.5 Renderer architecture

Use a structured `ReportDocument` AST and templates independent of the chat response renderer. Candidates discussed: **Quarto**, **Pandoc**, **Typst**, **Citation.js** and **Zotero Translation Server**. Prefer the smallest viable pipeline compatible with existing runtime; do not simultaneously introduce five rendering systems. Render untrusted user/archival text safely; external binaries and user-controlled templates need server-side sandbox limits.

- **HTML:** responsive report preview with embedded permitted media, expandable citations, map widgets and source-detail drawers.
- **PDF:** fixed report layout; downloadable and archival-ready when fonts/images/rights permit.
- **DOCX:** editable exported document; warn if interactive elements are flattened or omitted.
- **EPUB:** optional book mode with proper metadata, chapter navigation and asset licence declarations.

Citation anchors must survive exports; if a cultural item appears in more than one report section, reuse the same canonical citation and identify the edition/asset precisely.

# 28. UI extensions, source rights, micropayments and moderation

## 28.1 Archive Explorer / cultural tab

Keep the existing centre chat and right-hand side panel. Add `Cultural Discovery` as a contextual side-panel mode, not an additional top-level product. Reuse existing `Collection → Record → Preview → Save` behaviours. Optional tabs: **Art**, **Literature**, **Songs & Folklore**, **Film & Audio**, **Local Depictions**, **Saved**, with search, filters, compact cards, pagination and source-right badges.

A click should show: title, creator, source, dates, depicted geography/period, why relevant, media rights, provenance and an `Add to report` action. Side-by-side compare should allow an artwork, old map and person's biographical chronology to remain visible concurrently, with chat persistent. User can save a candidate to Research Basket without declaring it verified historical evidence.

## 28.2 Person and place pages

Add `Cultural context` beside the existing Story, Timeline, Gallery, Tree/Evidence and Map views. The user's own photographs belong in the ordinary Gallery; contextual paintings from museums are not automatically relabelled as family photos. On map pins, use explicit classes `historic_image`, `contemporary_illustration`, `literary_reference`, `recorded_song`, `later_fiction`, `original_document`.

The report builder should support drag-to-reorder blocks, approve/reject suggestions, highlight copyright limitations, display citation previews and permit a historical society/editor to contribute interpretative captions with revision history.

## 28.3 Rights ledger and payments

Extend the existing source-licensing registry (§17) with rights per **work**, **edition**, **specific media asset**, **excerpt** and **output context**. Distinguish `search/index`, `thumbnail`, `in-app full display`, `short excerpt`, `print/PDF`, `public website`, `commercial resale`, `AI processing` and `model training` permissions. These are distinct rights. Include attribution, territory, expiry, embargo, withdrawal, partner contract and fallback URL.

Where relevant, route licensed collections through existing contributor royalty and opt-in micro-donation ledger. A user who scrolls past 200 paintings should not accrue 200 micro-donations by default. Donation/royalty triggers must be explicitly defined and auditable. Distinguish charity donations from creator tips and licensing fees; permit monthly caps; no unexpected payment per citation or preview.

## 28.4 Trust, copyright, privacy and community annotation

- No automatic identification of private or living people in imagery based solely on facial similarity; use consent-based attribution and verified archival descriptions.
- Allow community annotations with review status and contributor attribution; never overwrite original cataloguer descriptions.
- Separate historic depictions of stereotypes and discrimination from contemporary objective description; contextualise as representations.
- Do not produce fabricated literary quotations or claim invented speech/diary entries came from primary sources.
- Record redaction/removal requests, public/private visibility and permissions for contemporary oral histories and family photos.
- For protected literary works or recordings, prefer contextual summary and links rather than reproducing material beyond permission.

# 29. Phased cultural build, acceptance tests and demonstration scenarios

## 29.1 Incremental phases

| Phase | Priority | Working deliverable | Principal candidates |
|---|---|---|---|
| C0 — Core cultural records | P0/P1 | `CulturalWork`, manifestations, rights, attribution, sources; fixtures and tests | Existing DB and connector framework |
| C1 — Art discovery | P1 | One real art dataset or API ingested/indexed; filtered grid and record details in Archive Explorer | Met Open Access or Cleveland Museum; IIIF where available |
| C2 — Literature | P1/P2 | Licensed/public-domain text index; search passage with source and edition; named places | Gutendex, Standard Ebooks, BookNLP/Stanza |
| C3 — Report preview | P1/P2 | One-click illustrated biography preview; editable blocks, citations, rights filtering | Existing AI, Citation.js, Quarto/Pandoc/Typst evaluation |
| C4 — Place and image links | P2 | Cultural works on historical map; image annotations and temporal labels | Locolligo, Annotorious, PostGIS, MapLibre |
| C5 — Music and folklore | P2/P3 | Catalogued songs, place/period associations and variants | VWML/Roud, Bodleian, music21, Verovio |
| C6 — Multimedia partnerships | P3 | Licensed/metadata linked video/audio and institutional collections | BFI/BBC/Pathé, partner agreement |
| C7 — Publishing and community | P3 | HTML/PDF/DOCX/EPUB and historian-curated cultural exhibits | Quarto/Pandoc/Typst, Home/Connect integration |

The early vertical slice should not be blocked by licensing large collections: use a small, explicitly reusable dataset and keep external-only catalogue cards where media is restricted.

## 29.2 Required acceptance tests

1. **Cultural evidence distinction:** A French peasant painting can be recommended for an English farm worker, but it is always labelled comparative/illustrative, never a direct record.
2. **Creator/depicted place distinction:** A painting created in one city depicting another is placed correctly on geographic layers.
3. **Dates:** A song collected in 1935 but said to have older origins does not acquire an unsupported medieval composition date.
4. **Copyright fallback:** Restricted artwork returns a metadata/link card in public PDF and HTML, without embedding an unauthorised asset.
5. **Literary provenance:** Any quoted passage has exact work/edition/source anchor and is not fabricated by the LLM.
6. **Bibliography:** Citations and credit captions survive the HTML-to-PDF/DOCX pipeline.
7. **User control:** Report generator proposes sources and layout but never publishes or buys material without approval.
8. **No false history:** Historical-context passages never present illustrative art or fiction as evidence about a specific ancestor.
9. **Privacy:** A private person or family photo cannot be surfaced to another user's cultural discovery results absent opt-in permission.
10. **Donation control:** Passive browsing never triggers unexpected micro-payments, and monthly donation caps are enforced.
11. **Performance:** Cultural search paginates; importing 100,000 metadata rows doesn't attempt to render all results in-browser.
12. **Reproducibility:** The report source manifest stores query/provider IDs, response/ingestion versions, source timestamps and rights state.

## 29.3 Demonstration cases

**Case A — Berkshire agricultural worker, c.1840–1890:** import GEDCOM, retrieve person facts/places, show agricultural occupation context, compare documentary evidence with art (e.g. Constable, Millet with regional caveat), period-appropriate texts and documented song metadata; publish an editable, cited HTML report and PDF if images licensed.

**Case B — Oxford, 1750–1850:** search map and dated visual depictions; add engravings, William Turner of Oxford artworks, contemporary travel texts/poetry and public-domain materials. Display location ties and distinguish time depicted vs created. Generate a place-based cultural history.

**Case C — Wiltshire childhood/institution c.1780:** explain the specific institution via sourced Old Poor Law material; suggest appropriate contemporaneous artistic/cultural material without inventing the brothers' experiences or treating later literary depictions as eyewitness accounts.

**Case D — Twentieth-century industry:** select a worker around 1950, find accessible film catalogues, local photographs, oral histories and literature; clearly separate historical documentaries from retrospective drama, and show catalogue links for restricted video.

# 30. VS Code implementation prompt for the cultural extension

Paste this prompt to a coding assistant **after placing this consolidated addendum alongside the original blueprint**. Inspect the real repo before making claims about what exists.

```text
You are incrementally implementing ArchiveHub, a chat-first historical research platform.
Read docs/ARCHIVEHUB_MASTER_BLUEPRINT.md and
     docs/ARCHIVEHUB_ADDENDUM_V3_2026-11-10.md (especially §§23–31).
The v3 addendum includes all v2 material: do not reimplement existing functionality.

Preserve the existing 4 user areas (Record, Research, Home, Connect), UI, chat,
Archive Explorer, projects, GEDCOM workflows, existing evidence/rights graph.
Do not replace the prototype wholesale. First inspect actual code and produce a
small actual-vs-required gap checklist. Read licences before copying any code.

Implement a minimal Cultural History Engine vertical slice:
1. Add CulturalWork, CulturalManifestation, CulturalRelation, CulturalExcerpt,
   per-asset rights, source provenance and date range fields with migrations.
2. Implement ONE vetted art provider (e.g. a Met Open Access snapshot or a
   documented museum API), including mocked fixtures for offline tests,
   server-side pagination, provider IDs, rights metadata and original links.
3. Add a 'Cultural Discovery' contextual right-panel tab with filters for
   period/place/theme/medium/representation type; source and rights details.
4. Implement an explanation of relevance and require approved relation status
   before depicting a proposed link as historical fact.
5. Build 'Generate Historical Report' as a draft-only, private-by-default
   HTML workflow with structured blocks, source manifest, bibliography and
   one eligible cultural image, with a metadata-only rights fallback.
6. Preserve the evidence/context/art distinction in the report and UI.
7. Add tests for dates, licensing, provenance, source quotes, privacy and
   no unexpected donations/publishing; include Berkshire and Oxford fixtures.

After completing that slice, propose separate incremental work for literary
search, historical place links, folklore catalogues, document export and
partner licensing. Do not bulk scrape restricted sources or pretend to have
API keys. If a source cannot be accessed legally, keep a provider stub with
'catalogue-only / requires agreement' status and a working external link.

Report code changes, tests, unverified assumptions and exact next actions.
```

# 31. Additional cultural documentation and links

## 31.1 Primary cultural collection sources

- Met metadata: <https://github.com/metmuseum/openaccess> and museum API <https://metmuseum.github.io/>
- Tate snapshot: <https://github.com/tategallery/collection>
- MoMA data: <https://github.com/MuseumofModernArt/collection>
- Cleveland Museum open API: <https://openaccess-api.clevelandart.org/>
- Art Institute API and bulk dataset: <https://api.artic.edu/docs/> and <https://github.com/art-institute-of-chicago/api-data>
- V&A collections API: <https://developers.vam.ac.uk/>
- Rijksmuseum linked data: <https://data.rijksmuseum.nl/>
- Wikimedia Commons: <https://commons.wikimedia.org/>
- Europeana API: <https://api.europeana.eu/>
- DPLA developer portal: <https://pro.dp.la/developers>
- UK cultural collections: <https://artuk.org/>, <https://digital.bodleian.ox.ac.uk/>, <https://www.londonpicturearchive.org.uk/>

## 31.2 Literary, song and media sources

- Project Gutenberg: <https://www.gutenberg.org/>; Gutendex: <https://github.com/garethbjohnson/gutendex>
- Standard Ebooks: <https://github.com/standardebooks> and <https://github.com/standardebooks/tools>
- Wikisource: <https://en.wikisource.org/>
- Open Library: <https://openlibrary.org/developers/api>
- Vaughan Williams Memorial Library and Roud catalogues: <https://www.vwml.org/>
- Traditional Ballad Index: <https://balladindex.org/>
- Bodleian digital collections: <https://digital.bodleian.ox.ac.uk/>
- Tobar an Dualchais: <https://www.tobarandualchais.co.uk/>
- Irish Traditional Music Archive: <https://www.itma.ie/>
- Folklore Society: <https://folklore-society.com/>
- BFI Archive: <https://www.bfi.org.uk/bfi-national-archive>
- British Pathé: <https://www.britishpathe.com/>

## 31.3 Open-source research and publishing

- Art datasets directory: <https://github.com/georgeblck/art-datasets>
- BookNLP: <https://github.com/booknlp/booknlp>
- CLTK: <https://github.com/cltk/cltk>
- Stanza: <https://github.com/stanfordnlp/stanza>
- GLAM Workbench: <https://github.com/GLAM-Workbench>
- music21: <https://github.com/cuthbertLab/music21>
- Humdrum data: <https://github.com/humdrum-tools/humdrum-data>
- Verovio Humdrum Viewer: <https://github.com/humdrum-tools/verovio-humdrum-viewer>
- Locolligo: <https://github.com/docuracy/Locolligo>
- INCEpTION: <https://github.com/inception-project/inception>
- Annotorious: <https://github.com/annotorious/annotorious>
- Quarto: <https://github.com/quarto-dev/quarto-cli>
- Pandoc: <https://github.com/jgm/pandoc>
- Typst: <https://github.com/typst/typst>
- Citation.js: <https://github.com/citation-js/citation-js>
- Zotero Translation Server: <https://github.com/zotero/translation-server>

---

## Consolidated implementation principle (v3)

**ArchiveHub should make the historical record vivid without sacrificing its evidential integrity.** It must distinguish documented facts about a person or place, historically grounded social context, artistic interpretation, and later fictional representations. Cultural media enriches the user's understanding but does not silently become evidence. Preserve the four-area, chat-first architecture; develop cultural discovery in the side panel; and make a cited, editable, rights-aware illustrated report an end-to-end demonstration of how those systems fit together.
