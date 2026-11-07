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


@pytest.fixture
def calls(monkeypatch, settings):
    for k, v in KEYS.items():
        setattr(settings, k, v)
    settings.TNA_DISCOVERY_ENABLED = True
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


@pytest.mark.parametrize("key", sorted(CASES))
def test_without_a_key_it_says_so_and_calls_nothing(key, monkeypatch, settings):
    for k in KEYS:
        setattr(settings, k, "")
    settings.TNA_DISCOVERY_ENABLED = False

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
