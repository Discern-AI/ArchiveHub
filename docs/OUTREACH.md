# Outreach: ready-to-send requests

Drafts for the requests only the owner can make. Fill in the [brackets], send, then update the row's status here and in [SOURCE_REGISTER.md](SOURCE_REGISTER.md). Most important first.

| # | To | What it unlocks | Status |
|---|---|---|---|
| 1 | The National Archives | Discovery API (Royal Berkshire Archives and ~2,500 others) | Not sent |
| 2 | National Library of Scotland | Commercial use of historic OS map layers on the time map | Not sent |
| 3 | Europeana | Project API key | Not requested |
| 4 | Free keys (GeoNames, OpenAlex, Geograph, OS Data Hub, DigitalNZ, DPLA) | More sources in Search and the assistant | Not requested |
| 5 | Royal Berkshire Archives | Launch partnership | Not sent |
| 6 | West Berkshire Museum | Launch partnership | Not sent |
| 7 | National Library of Australia (Trove) | Commercial use of Trove | Not sent |
| 8 | Open Library, UK PlanIt | Permission for commercial use | Not sent |
| 9 | Free UK Genealogy | Bulk FreeBMD, FreeREG, FreeCEN indexes | Not sent |
| 10 | UK Data Service | I-CeM census microdata | Not sent |

---

## 1. The National Archives: Discovery API access

**To:** webmaster@nationalarchives.gov.uk
**Subject:** Discovery API access request: ArchiveHub (family and local history)

> Hello,
>
> I'd like to request access to the Discovery API for ArchiveHub, a platform where people research and preserve family and local history. We're piloting in Newbury and West Berkshire.
>
> - **Website:** [site address]
> - **Server IP address:** [IP address the API server will call from]
> - **How we'd use it:** when someone searches, we query Discovery live and show catalogue descriptions with a link to the record in Discovery, so they can find where documents are held (often the Royal Berkshire Archives) and order or visit them.
> - **Your terms:** we don't cache or store anything the API returns. Results are shown for that search only, and saved items keep just the Discovery link. We send at most one request a second and expect well under 3,000 calls a day.
> - **Contact:** [name, email]
>
> Our requests identify themselves with the User-Agent "ArchiveHubBot/0.1 (https://github.com/Discern-AI/ArchiveHub)".
>
> Thank you,
> [name]

**After approval:** set `TNA_DISCOVERY_ENABLED=true` in `services/api/.env`.

## 2. National Library of Scotland: historic maps for a commercial service

**To:** maps@nls.uk
**Subject:** Using NLS historic OS map layers in a commercial family history service

> Hello,
>
> ArchiveHub is a family and local history platform, piloting in Newbury. Our time map lets people move through the years and see records, photos and memories on the map, and we'd like to show your georeferenced OS six-inch (1888–1913), 1:25,000 (1937–61) and 1920s–40s layers underneath.
>
> We'd use the layers through MapTiler, credit the National Library of Scotland with a link wherever they appear (CC BY 3.0), and take a paid MapTiler plan before launch. As we'll be a commercial service (subscriptions and credits), could you confirm that this use is acceptable, or tell us what else you'd need?
>
> We'd also be interested in your Data Foundry map collections and the historical boundaries, if there's a route for commercial use.
>
> Thank you,
> [name, website, email]

**Then:** create a MapTiler account, set `MAPTILER_KEY`, restrict the key to our domains in MapTiler.

## 3. Europeana project API key

**Where:** the API key request form on pro.europeana.eu. Ask for a **project** key, not a personal one.

**Project description to paste:**

> ArchiveHub is a family and local history platform (piloting in Newbury and West Berkshire). Users search connected collections, including Europeana, from an explorer panel and from a research assistant that cites its sources. We show metadata with a link to each item on Europeana and its provider, respect each item's rights statement, and only show images where the rights allow. Production service; expected volume: [estimate] requests a day.

**Then:** set `EUROPEANA_API_KEY`.

## 4. Free keys (a few minutes each)

| Service | Where | Setting |
|---|---|---|
| OpenAlex | openalex.org/settings/api | `OPENALEX_API_KEY` |
| GeoNames | geonames.org: create an account, then switch on "free web services" in the account page | `GEONAMES_USERNAME` |
| Geograph | geograph.org.uk: Help, then API, then request a key | `GEOGRAPH_API_KEY` |
| OS Data Hub | osdatahub.os.uk: create a project, add the OS Names API (free plan) | `OS_DATA_HUB_KEY` |
| DigitalNZ | digitalnz.org: create an account, then "My API key" (commercial terms) | `DIGITALNZ_API_KEY` |
| DPLA | dp.la API page: request a key by email; read their terms first | `DPLA_API_KEY` |

Restart the API after adding keys. Each source then appears in the Explorer, Search ("Also search outside sources") and the assistant.

## 5. Royal Berkshire Archives: launch partner

**To:** [Royal Berkshire Archives enquiries address]
**Subject:** ArchiveHub: a Newbury family and local history pilot

> Hello,
>
> I'm building ArchiveHub, a place where people record, research and publish family and local history, starting with Newbury and West Berkshire. It already shows your catalogue entries (via TNA Discovery) alongside other evidence, so someone researching, say, a Cheap Street pub is pointed to your sale particulars and licensing records, with a link to order or visit.
>
> I'd love to talk about working together: sending researchers your way, crediting your collections clearly, and perhaps helping digitise, transcribe or describe material you'd like to make more findable, on terms you set. Would you have half an hour in the next few weeks?
>
> [name, website, email]

## 6. West Berkshire Museum: launch partner

**To:** [museum contact]
**Subject:** Newbury's history on a time map: would the museum like to be involved?

> Hello,
>
> ArchiveHub is a new family and local history platform piloting in Newbury. Its time map lets people slide through the years on Cheap Street and see records, listed buildings, old map names, photos and memories in one place, with public and private material clearly separate.
>
> We'd like the museum to be a launch partner: your objects and photos credited and linked, visitors directed to you, and perhaps a shared project collecting local memories with proper consent. Could we meet to talk it through?
>
> [name, website, email]

## 7. National Library of Australia: Trove commercial use

**Where:** Trove API key application (commercial access level), or the Trove contact form.

> ArchiveHub, a family history platform, would like to search Trove's digitised newspapers so users can find relatives who emigrated to Australia. We show each article's heading, date and newspaper with a link to read it on Trove, acknowledge Trove and the National Library of Australia, and don't bulk download. As we're a commercial service, we're asking for the commercial access level. Expected volume: [estimate] requests a day.

**Then:** set `TROVE_API_KEY`.

## 8. Open Library and UK PlanIt: commercial use

**Open Library**, to openlibrary@archive.org:

> ArchiveHub (family and local history) would like to use the Open Library search API to suggest books about a place or subject, with links to Open Library. Requests would be made on behalf of individual users, identified by our User-Agent, a few per search, never bulk. As we're a commercial service, is this acceptable, or should we use the monthly data dumps instead?

**UK PlanIt**, via planit.org.uk's contact page:

> ArchiveHub would like to show planning applications near a building on our time map (reference, date, description and a link to the council's page), using your API at modest volumes. We're a commercial service. Is that acceptable, and is there anything you'd like us to credit or pay?

## 9. Free UK Genealogy: bulk data for research

**Where:** freeukgenealogy.org.uk/bulk-data-for-research (read their terms first)

> Hello,
>
> ArchiveHub is a family and local history platform piloting in Newbury and West Berkshire. We'd like to explore bulk access to FreeBMD, FreeREG and FreeCEN indexes so people can find entries alongside their own records, with every result credited to Free UK Genealogy and its volunteers and linked back to your sites.
>
> Public benefit: people would be pointed to original records and official sources (GRO, record offices) rather than paywalls, and we'd like to support the volunteer projects financially as the platform grows. We'd follow whatever scope and terms you set, including no redistribution of the data.
>
> Could we talk about whether this fits your bulk data programme?
>
> [name, website, email]

## 10. UK Data Service: I-CeM census microdata

**Where:** UK Data Service enquiries.

> ArchiveHub is a family and local history platform. We're interested in two things: (1) the statistical I-CeM data to describe occupations, households and migration in a place and period, shown as context (never about named individuals); and (2) whether named-record access could ever be licensed for a public historical research service, and on what terms. Could you advise on both?
