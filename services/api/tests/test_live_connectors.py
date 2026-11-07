"""Connectors that need a key or registered access (ADR-034).

Responses for Europeana, TNA Discovery, DigitalNZ and Geograph are trimmed from real
responses (7 Nov 2026). Trove, DPLA and OS Names follow their documented formats, as
they can't be called without a key.
"""

import json
import urllib.error

import pytest

from assistant.tools import ToolKit
from connectors import sources
from connectors.base import BadQuery, NotFound
from connectors.live import (
    LIVE_CONNECTORS,
    NotConfigured,
    TNADiscoveryConnector,
    bng_to_wgs84,
)
from connectors.sources import CONNECTORS
from explorer.models import BasketItem
from history.loader import load_all
from projects.models import Project

pytestmark = pytest.mark.django_db
JSON = "application/json"
KEYS = {
    "EUROPEANA_API_KEY": "eu-secret",
    "TROVE_API_KEY": "trove-secret",
    "DIGITALNZ_API_KEY": "dnz-secret",
    "DPLA_API_KEY": "dpla-secret",
    "GEOGRAPH_API_KEY": "geo-secret",
    "OS_DATA_HUB_KEY": "os-secret",
}

EU_ITEM = {
    "id": "/109/https___hispana_mcu_es_lod_oai_bvpb_mcu_es_441203_ent0",
    "title": ["A Map of the Country ten miles round Newbury in Berkshire"],
    "dcDescription": ["Engraved map."],
    "guid": "https://www.europeana.eu/item/109/https___hispana_mcu_es_lod_oai_bvpb_mcu_es_441203_ent0",
    "year": ["1768"],
    "type": "IMAGE",
    "dataProvider": ["Virtual Library of Bibliographical Heritage"],
    "rights": ["http://creativecommons.org/licenses/by/4.0/"],
    "edmIsShownAt": ["https://bvpb.mcu.es/es/consulta/registro.do?id=441203"],
}
EU_ITEM_2 = {**EU_ITEM, "id": "/2059209/5516", "title": ["Newbury, Berkshire"], "year": []}
TNA_REC = {
    "id": "e554294c-7116-4d89-8f2a-d2697edec0ed",
    "title": "Sale particulars of 62 Cheap Street, Newbury.",
    "description": "",
    "coveringDates": "1933,[1970s]",
    "reference": "D/EX 898/2/284/1-2",
    "heldBy": ["Royal Berkshire Archives"],
    "context": "Records of Neates of Hungerford and Newbury, estate agents.",
}
TNA_REC_2 = {**TNA_REC, "id": "C261066", "title": "Newbury: Cheap Street"}
TNA_DETAIL = {
    "id": TNA_REC["id"],
    "title": TNA_REC["title"],
    "coveringDates": "1933,[1970s]",
    "citableReference": "D/EX 898/2/284/1-2",
    "heldBy": [{"xReferenceName": "Royal Berkshire Archives"}],
    "scopeContent": {"description": None},
}
DNZ_REC = {
    "id": 38516251,
    "title": "Picturesque setting for an English pheasant shoot",
    "description": "Hounds and members of a pheasant shoot party at Yattendon near Newbury.",
    "display_content_partner": "Auckland Libraries",
    "category": ["Images"],
    "display_date": "1934-02-07",
    "source_url": "http://api.digitalnz.org/records/38516251/source",
    "landing_url": "https://kura.aucklandlibraries.govt.nz/digital/collection/photos/id/261102",
    "rights": "No known copyright restrictions",
    "usage": ["Share", "Modify", "Use commercially"],
}
GEO_ITEM = {
    "title": "SU4767 : West Berkshire : Newbury Scenery",
    "description": "Looking down towards the town of Newbury.",
    "link": "https://www.geograph.org.uk/photo/5442107",
    "author": "Lewis Clarke",
    "guid": "5442107",
    "imageTaken": "2017-06-18",
    "lat": "51.404546",
    "long": "-1.318518",
    "thumb": "https://s3.geograph.org.uk/geophotos/05/44/21/5442107_4004776e_120x120.jpg",
    "licence": "http://creativecommons.org/licenses/by-sa/2.0/",
}
GEO_ITEM_2 = {**GEO_ITEM, "guid": "54331", "title": "SU4767 : Kennet Bridge, Newbury"}
GEO_OEMBED = {
    "type": "photo",
    "title": "West Berkshire : Newbury Scenery",
    "description": "Looking down towards the town of Newbury.",
    "author_name": "Lewis Clarke",
    "web_page": "https://www.geograph.org.uk/photo/5442107",
    "thumbnail_url": "https://s3.geograph.org.uk/x_120x120.jpg",
    "license": "Attribution-ShareAlike License",
    "license_url": "http://creativecommons.org/licenses/by-sa/2.0/",
    "geo": {"lat": "51.404546", "long": "-1.318518", "square": "SU4767"},
}
TROVE_ART = {
    "id": "12345678",
    "heading": "NEWS FROM HOME. Newbury, Berkshire.",
    "title": {"id": "35", "title": "The Sydney Morning Herald (NSW : 1842 - 1954)"},
    "date": "1901-03-02",
    "page": "7",
    "snippet": "a letter from <strong>Newbury</strong>",
    "troveUrl": "https://trove.nla.gov.au/newspaper/article/12345678",
}
DPLA_DOC = {
    "id": "0123456789abcdef0123456789abcdef",
    "isShownAt": "https://example.org/item/1",
    "dataProvider": {"name": "Example Historical Society"},
    "rights": "http://rightsstatements.org/vocab/NoC-US/1.0/",
    "sourceResource": {
        "title": ["Letter from Newbury, England"],
        "description": ["A letter home."],
        "date": [{"displayDate": "1888"}],
        "type": ["text"],
    },
}
OS_ENTRY = {
    "ID": "osgb4000000074568992",
    "NAMES_URI": "http://data.ordnancesurvey.co.uk/id/4000000074568992",
    "NAME1": "Cheap Street",
    "TYPE": "transportNetwork",
    "LOCAL_TYPE": "Named Road",
    "GEOMETRY_X": 447300.0,
    "GEOMETRY_Y": 166900.0,
    "POSTCODE_DISTRICT": "RG14",
    "POPULATED_PLACE": "Newbury",
    "COUNTY_UNITARY": "West Berkshire",
}


HE_FEATURE = {
    "attributes": {
        "ListEntry": 1220923,
        "Name": "No. 6 CHEAP STREET",
        "Grade": "II",
        "ListDate": 431308800000,
        "hyperlink": "https://historicengland.org.uk/listing/the-list/list-entry/1220923",
    },
    "geometry": {"points": [[-1.32138815234494, 51.3983980369856]]},
}
HE_OLD = {  # listed before 1970: a negative timestamp
    **HE_FEATURE,
    "attributes": {**HE_FEATURE["attributes"], "ListEntry": 1220925, "ListDate": -607737600000},
}
GAZ_ENTRY = {
    "id": "https://www.thegazette.co.uk/Edinburgh/issue/12396/page/995",
    "title": "The Edinburgh Gazette, Issue 12396, Page 995",
    "published": "1911-10-06T00:00:00",
    "content": "<div><p>Temporary Assistant Postmen — Newbury…</p></div>",
}
GAZ_NOTICE = {
    "id": "https://www.thegazette.co.uk/id/notice/3679551",
    "title": " A Name ",
    "published": "1920-11-21T01:00:05",
    "category": {"@term": "Deceased Estates"},
    "geo:Point": {"geo:lat": "51.6", "geo:long": "-1.2"},
    "content": "<div>Address of Deceased</div>",
}
GEONAME = {
    "geonameId": 2641741,
    "name": "Newbury",
    "lat": "51.40148",
    "lng": "-1.32471",
    "fcodeName": "seat of a second-order administrative division",
    "fclName": "city, village,...",
    "adminName1": "England",
    "countryName": "United Kingdom",
    "countryCode": "GB",
    "population": 41075,
}


MET_OBJECT = {
    "objectID": 1589,
    "title": "Side Chair",
    "objectDate": "ca. 1700",
    "objectName": "Side chair",
    "isPublicDomain": True,
    "primaryImageSmall": "https://images.metmuseum.org/x.jpg",
    "objectURL": "https://www.metmuseum.org/art/collection/search/1589",
    "department": "The American Wing",
}
MET_IN_COPYRIGHT = {**MET_OBJECT, "objectID": 646786, "title": "Stables", "isPublicDomain": False}
AIC_ART = {
    "id": 211099,
    "title": "John Q. Public",
    "date_display": "1943",
    "artist_display": "Cartoonist, American",
    "artwork_type_title": "Drawing",
    "is_public_domain": True,
    "image_id": "abc",
}
OA_WORK = {
    "id": "https://openalex.org/W4392071046",
    "display_name": "Town and Countryside in western Berkshire",
    "publication_year": 2007,
    "type": "book",
    "authorships": [{"author": {"display_name": "M. Yates"}}],
    "primary_location": {"source": {"display_name": "Boydell"}, "landing_page_url": "https://x"},
    "doi": "https://doi.org/10.1/abc",
}


@pytest.fixture
def calls(monkeypatch, settings):
    for k, v in KEYS.items():
        setattr(settings, k, v)
    settings.TNA_DISCOVERY_ENABLED = True
    settings.GEONAMES_USERNAME = "geo-user"
    seen: list[dict] = []

    def fake(url, params, timeout=10.0, headers=None):
        seen.append({"url": url, "params": dict(params), "headers": dict(headers or {})})
        p = params
        if "europeana" in url:
            if p["query"].startswith("europeana_id:"):
                wanted = p["query"].split('"')[1]
                items = [i for i in (EU_ITEM, EU_ITEM_2) if i["id"] == wanted]
                return {"success": True, "items": items}
            if p.get("cursor") == "*":
                return {"success": True, "items": [EU_ITEM], "nextCursor": "AoE2"}
            return {"success": True, "items": [EU_ITEM_2]}
        if "nationalarchives" in url:
            if "/details/" in url:
                if url.endswith(TNA_REC["id"]):
                    return TNA_DETAIL
                raise NotFound("404")
            page = p["sps.page"]
            return {"records": [TNA_REC] if page == 1 else [TNA_REC_2], "count": 2}
        if "digitalnz" in url:
            if url.endswith("records.json"):
                rec = DNZ_REC if p["page"] == 1 else {**DNZ_REC, "id": 19476025}
                return {"search": {"result_count": 2, "results": [rec]}}
            if "38516251" in url:
                return {"record": DNZ_REC}
            raise NotFound("404")
        if "geograph" in url:
            if url.endswith("oembed"):
                return GEO_OEMBED if "5442107" in p["url"] else {"error": "not found"}
            if "i" in p:
                return {"items": [GEO_ITEM_2]}
            return {
                "items": [GEO_ITEM],
                "nextURL": "https://www.geograph.org.uk/feed/results/220442558/2.json",
            }
        if "trove" in url:
            if url.endswith("/result"):
                art = TROVE_ART if p["s"] == "*" else {**TROVE_ART, "id": "87654321"}
                nxt = "AoIx" if p["s"] == "*" else None
                return {
                    "category": [
                        {"code": "newspaper", "records": {"article": [art], "nextStart": nxt}}
                    ]
                }
            if url.endswith("12345678"):
                return {"article": TROVE_ART}
            raise NotFound("404")
        if "dp.la" in url:
            if url.endswith("/items"):
                doc = DPLA_DOC if p["page"] == 1 else {**DPLA_DOC, "id": "f" * 32}
                return {"count": 2, "docs": [doc]}
            if url.endswith(DPLA_DOC["id"]):
                return {"docs": [DPLA_DOC]}
            return {"docs": []}
        if "api.os.uk" in url:
            off = p.get("offset", 0)
            entry = OS_ENTRY if off == 0 else {**OS_ENTRY, "ID": "osgb2", "NAME1": "Cheap Street"}
            return {"header": {"totalresults": 2}, "results": [{"GAZETTEER_ENTRY": entry}]}
        if "arcgis.com" in url:
            if p["where"].startswith("ListEntry="):
                n = int(p["where"].split("=")[1])
                return {
                    "features": [
                        f for f in (HE_FEATURE, HE_OLD) if f["attributes"]["ListEntry"] == n
                    ]
                }
            if p["resultOffset"] == 0:
                return {"features": [HE_FEATURE], "exceededTransferLimit": True}
            return {"features": [HE_OLD]}
        if "thegazette" in url:
            entry = GAZ_ENTRY if p["results-page"] == 1 else GAZ_NOTICE
            return {"f:total": "2", "entry": [entry]}
        if "geonames" in url:
            if url.endswith("getJSON"):
                return (
                    GEONAME
                    if p["geonameId"] == "2641741"
                    else {"status": {"value": 15, "message": "no record"}}
                )
            if p["startRow"] == 0:
                return {"totalResultsCount": 2, "geonames": [GEONAME]}
            return {"totalResultsCount": 2, "geonames": [{**GEONAME, "geonameId": 1}]}
        if "metmuseum" in url:
            if "/search" in url:
                ids = [646786, 999999] if p["offset"] == 0 else [1589]
                return {"total": 3, "objectIDs": ids}
            if url.endswith("/646786"):
                return MET_IN_COPYRIGHT
            if url.endswith("/1589"):
                return MET_OBJECT
            raise NotFound("404")
        if "artic.edu" in url:
            config = {"iiif_url": "https://www.artic.edu/iiif/2"}
            if url.endswith("/search"):
                art = (
                    AIC_ART
                    if p["page"] == 1
                    else {**AIC_ART, "id": 25406, "is_public_domain": False}
                )
                return {"data": [art], "pagination": {"total_pages": 2}, "config": config}
            if url.endswith("/211099"):
                return {"data": AIC_ART, "config": config}
            return {"data": {}}
        if "openalex" in url:
            if url.endswith("/works"):
                work = OA_WORK if p["page"] == 1 else {**OA_WORK, "id": "https://openalex.org/W2"}
                return {"meta": {"count": 2}, "results": [work]}
            if url.endswith("W4392071046"):
                return OA_WORK
            raise NotFound("404")
        raise AssertionError(f"unexpected {url}")

    monkeypatch.setattr(sources, "http_get_json", fake)
    return seen


CASES = {
    "europeana": ("Newbury", EU_ITEM["id"].lstrip("/")),
    "tna-discovery": ("Cheap Street Newbury", TNA_REC["id"]),
    "digitalnz": ("Newbury", "38516251"),
    "geograph": ("SU4767", "5442107"),
    "trove": ("Newbury Berkshire", "12345678"),
    "dpla": ("Newbury", DPLA_DOC["id"]),
    "os-names": ("Cheap Street Newbury", f"{OS_ENTRY['ID']}~Cheap Street"),
    "historic-england": ("Cheap Street", "1220923"),
    "the-gazette": ("Spracklen Newbury", "Edinburgh/issue/12396/page/995"),
    "geonames": ("Newbury", "2641741"),
    "met-museum": ("Newbury", "1589"),
    "art-institute-chicago": ("shoemaker", "211099"),
    "openalex": ("Newbury Berkshire", "W4392071046"),
}


@pytest.fixture(params=sorted(CASES))
def case(request, calls):
    query, known = CASES[request.param]
    return CONNECTORS[request.param], query, known


def test_every_live_connector_is_registered_and_tested():
    assert {c.key for c in LIVE_CONNECTORS} == set(CASES)


def test_contract_search_record_and_paging(case):
    connector, query, known = case
    page = connector.search(query, page_size=1)
    assert page.records and page.next_cursor and page.searched
    first = page.records[0]
    assert first.connector == connector.key and first.id and first.title and first.rights
    second = connector.search(query, cursor=page.next_cursor, page_size=1).records
    assert second and second[0].id != first.id
    record = connector.get_record(known)
    assert record.id == known and record.title
    assert connector.citation(record)
    assert connector.storage_policy(record) in {
        "full_copy",
        "metadata_only",
        "reference_only",
        "none",
    }


def test_contract_unknown_record_and_bad_input(case):
    connector, query, _ = case
    with pytest.raises(NotFound):
        connector.get_record("zz-not-a-real-id")
    with pytest.raises(BadQuery):
        connector.search(query, cursor="!!not a cursor")
    with pytest.raises(BadQuery):
        connector.search("   ")


OPEN = {"historic-england", "the-gazette", "met-museum", "art-institute-chicago", "openalex"}


@pytest.mark.parametrize("key", sorted(set(CASES) - OPEN))
def test_without_a_key_it_says_so_and_calls_nothing(key, monkeypatch, settings):
    for k in KEYS:
        setattr(settings, k, "")
    settings.TNA_DISCOVERY_ENABLED = False
    settings.GEONAMES_USERNAME = ""

    def never(*a, **kw):
        raise AssertionError("no request without a key")

    monkeypatch.setattr(sources, "http_get_json", never)
    connector = CONNECTORS[key]
    assert connector.describe()["configured"] is False
    with pytest.raises(NotConfigured) as exc:
        connector.search("Newbury")
    assert exc.value.user_message == "This source isn't set up on this server yet."


def test_keys_travel_in_headers_where_supported(calls):
    CONNECTORS["trove"].search("Newbury")
    CONNECTORS["digitalnz"].search("Newbury")
    trove, dnz = calls[-2], calls[-1]
    assert trove["headers"] == {"X-API-KEY": "trove-secret"}
    assert dnz["headers"] == {"Authentication-Token": "dnz-secret"}
    assert "trove-secret" not in json.dumps(trove["params"])


def test_errors_never_reveal_keys(monkeypatch, settings):
    settings.EUROPEANA_API_KEY = "eu-secret"

    def boom(request, timeout, context=None):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(sources.urllib.request, "urlopen", boom)
    with pytest.raises(Exception) as exc:
        CONNECTORS["europeana"].search("Newbury")
    assert "eu-secret" not in str(exc.value)


def test_explorer_lists_sources_that_need_setting_up(alice_client, settings):
    for k in KEYS:
        setattr(settings, k, "")
    settings.TNA_DISCOVERY_ENABLED = False
    sources_ = {s["key"]: s for s in alice_client.get("/api/v1/explorer/sources").json()}
    assert sources_["europeana"]["available"] is False
    assert "project API key" in sources_["europeana"]["note"]
    assert "IP address" in sources_["tna-discovery"]["note"]
    r = alice_client.get("/api/v1/explorer/europeana/search", {"q": "Newbury"})
    assert r.status_code == 503 and "isn't set up" in r.json()["detail"]


def test_explorer_opens_records_whose_ids_contain_slashes(calls, alice_client):
    rid = EU_ITEM["id"].lstrip("/")
    r = alice_client.get(f"/api/v1/explorer/europeana/records/{rid}")
    assert r.status_code == 200 and r.json()["id"] == rid


def test_tna_results_are_never_stored(calls, alice, alice_client):
    load_all()
    project = Project.objects.create(owner=alice, title="P")
    r = alice_client.post(
        f"/api/v1/projects/{project.id}/basket",
        {"connector": "tna-discovery", "record_id": TNA_REC["id"]},
        content_type=JSON,
    )
    assert r.status_code == 201
    item = BasketItem.objects.get()
    assert "Cheap Street" not in item.title and item.snapshot is None
    assert item.url.endswith(TNA_REC["id"])

    kit = ToolKit(user=alice)
    content, is_error = kit.run("search_connector", {"source": "tna-discovery", "query": "Cheap"})
    assert not is_error and "Cheap Street" in content  # used for this answer
    saved = kit.stored_result("search_connector", {"source": "tna-discovery"}, content)
    assert "Cheap Street" not in saved and "aren't kept" in saved
    assert all("Cheap Street" not in c.label for c in kit.citations.values())
    # Other sources' results are kept as they are.
    other = kit.stored_result("search_connector", {"source": "europeana"}, content)
    assert other == content


def test_assistant_says_when_a_source_is_not_set_up(alice, settings, monkeypatch):
    settings.DPLA_API_KEY = ""
    kit = ToolKit(user=alice)
    content, _ = kit.run("search_connector", {"source": "dpla", "query": "Newbury"})
    assert "isn't set up" in content
    assert any(c["status"] == "Couldn't access" for c in kit.checked)


def test_tna_waits_between_requests(calls, monkeypatch):
    slept = []
    monkeypatch.setattr("connectors.live.time.sleep", lambda s: slept.append(s))
    TNADiscoveryConnector._last = 0.0
    c = CONNECTORS["tna-discovery"]
    c.search("Newbury")
    c.search("Newbury")
    assert slept and 0 < slept[-1] <= 1.0


def test_record_details(calls):
    eu = CONNECTORS["europeana"].get_record(EU_ITEM["id"].lstrip("/"))
    assert eu.date_text == "1768" and "by/4.0" in eu.rights
    tna = CONNECTORS["tna-discovery"].get_record(TNA_REC["id"])
    assert tna.fields == {"reference": "D/EX 898/2/284/1-2", "held_by": "Royal Berkshire Archives"}
    geo = CONNECTORS["geograph"].get_record("5442107")
    assert geo.attribution == "Lewis Clarke, via Geograph" and geo.latitude == pytest.approx(
        51.4045
    )
    dnz = CONNECTORS["digitalnz"].search("Newbury").records[0]
    assert dnz.url.endswith("/source") and dnz.attribution == "Auckland Libraries"
    trove = CONNECTORS["trove"].search("Newbury").records[0]
    assert trove.description == "a letter from Newbury"  # markup stripped
    assert trove.fields["newspaper"].startswith("The Sydney Morning Herald")
    os_ = CONNECTORS["os-names"].search("Cheap Street").records[0]
    assert os_.latitude == pytest.approx(51.399, abs=0.002)
    assert os_.longitude == pytest.approx(-1.321, abs=0.002)


def test_bng_to_wgs84_matches_ordnance_survey():
    # Ordnance Survey's worked example (TG 51409 13177) and Ben Nevis.
    lat, lng = bng_to_wgs84(651409.903, 313177.270)
    assert lat == pytest.approx(52.65798, abs=0.0001) and lng == pytest.approx(1.71605, abs=0.0001)
    lat, lng = bng_to_wgs84(216666, 771288)
    assert lat == pytest.approx(56.7969, abs=0.001) and lng == pytest.approx(-5.0037, abs=0.001)


def test_open_sources_are_always_set_up(settings):
    for key in OPEN:
        assert CONNECTORS[key].describe()["configured"] is True


def test_historic_england_searches_near_a_named_town(calls):
    load_all()  # Newbury has a location
    page = CONNECTORS["historic-england"].search("Cheap Street Newbury")
    sent = calls[-1]["params"]
    assert sent["where"] == "UPPER(Name) LIKE '%CHEAP%' AND UPPER(Name) LIKE '%STREET%'"
    assert sent["geometryType"] == "esriGeometryEnvelope" and sent["inSR"] == 4326
    assert "near Newbury" in page.searched
    record = page.records[0]
    assert record.date_text == "Listed 1983" and record.latitude == pytest.approx(51.3984)
    old = CONNECTORS["historic-england"].get_record("1220925")
    assert old.date_text == "Listed 1950"  # before 1970
    # Only letters and digits reach the query.
    CONNECTORS["historic-england"].search("Cheap' OR 1=1 --")
    assert "'" not in calls[-1]["params"]["where"].replace("LIKE '%", "").replace("%'", "")


def test_gazette_only_searches_notices_a_century_old(calls):
    page = CONNECTORS["the-gazette"].search("Spracklen", page_size=1)
    cutoff = calls[-1]["params"]["end-publish-date"]
    import time

    assert cutoff == f"{time.gmtime().tm_year - 100}-12-31"
    assert f"up to {cutoff[:4]}" in page.searched
    notice = (
        CONNECTORS["the-gazette"]
        .search("Spracklen", cursor=page.next_cursor, page_size=1)
        .records[0]
    )
    assert notice.id == "notice/3679551" and notice.record_type == "deceased estates"
    # Opening a record never fetches it: only the link is shown.
    before = len(calls)
    r = CONNECTORS["the-gazette"].get_record("notice/3679551")
    assert len(calls) == before and r.url == "https://www.thegazette.co.uk/notice/3679551"


def test_gazette_keeps_to_its_fair_use_rate(calls, monkeypatch):
    from connectors.live import GazetteConnector

    slept = []
    monkeypatch.setattr("connectors.live.time.sleep", lambda s: slept.append(s))
    GazetteConnector._last = 0.0
    CONNECTORS["the-gazette"].search("Newbury")
    CONNECTORS["the-gazette"].search("Newbury")
    assert slept and 1.0 < slept[-1] <= 2.0


def test_geonames_errors_are_mapped(calls, monkeypatch):
    from connectors.base import AccessDenied, RateLimited

    def status(value):
        def fake(url, params, timeout=10.0, headers=None):
            return {"status": {"value": value, "message": "x"}}

        return fake

    for value, error in ((10, AccessDenied), (19, RateLimited), (15, NotFound)):
        monkeypatch.setattr(sources, "http_get_json", status(value))
        with pytest.raises(error):
            CONNECTORS["geonames"].search("Newbury")


def test_museum_images_only_for_public_domain_objects(calls):
    met = CONNECTORS["met-museum"]
    page = met.search("Newbury", page_size=2)
    # A withdrawn object (404) is skipped rather than failing the search.
    assert [r.id for r in page.records] == ["646786"]
    assert "image" not in page.records[0].fields and "reserved" in page.records[0].rights
    assert met.get_record("1589").fields["image"].startswith("https://images.metmuseum.org/")
    aic = CONNECTORS["art-institute-chicago"].search("shoemaker", page_size=1)
    assert aic.records[0].fields["image"].endswith("/abc/full/400,/0/default.jpg")
    assert calls[-1]["headers"]["AIC-User-Agent"].startswith("ArchiveHub")
    assert "description" not in calls[-1]["params"]["fields"]  # CC BY text left out
    second = CONNECTORS["art-institute-chicago"].search(
        "shoemaker", cursor=aic.next_cursor, page_size=1
    )
    assert "image" not in second.records[0].fields


def test_openalex_uses_a_key_only_when_set(calls, settings):
    settings.OPENALEX_API_KEY = ""
    CONNECTORS["openalex"].search("Newbury")
    assert "api_key" not in calls[-1]["params"]
    settings.OPENALEX_API_KEY = "oa-secret"
    record = CONNECTORS["openalex"].search("Newbury").records[0]
    assert calls[-1]["params"]["api_key"] == "oa-secret"
    assert record.url == "https://doi.org/10.1/abc" and record.date_text == "2007"
