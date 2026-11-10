"""Connector contract harness: every connector must behave the same way (SPEC §9)."""

import io
import ssl
import struct
import urllib.error
import zipfile

import pytest
from django.core.management import call_command

from connectors import sources
from connectors.base import AccessDenied, BadQuery, NotFound, RateLimited, Unavailable
from connectors.gb1900 import Pin, best_reading, parse_ewkb_point
from connectors.models import Dataset, DatasetRow
from connectors.sources import (
    CONNECTORS,
    OldMapNamesConnector,
    ReferenceConnector,
    WikidataConnector,
)
from history.loader import load_all

pytestmark = pytest.mark.django_db


# --- A tiny synthetic GB1900-format archive -----------------------------------------


def ewkb(lat: float, lon: float) -> str:
    return (b"\x01" + struct.pack("<I", 0x20000001) + struct.pack("<I", 4326)
            + struct.pack("<dd", lon, lat)).hex().upper()  # fmt: skip


def utf16_csv(header: list[str], rows: list[list[str]]) -> bytes:
    lines = [",".join(header)] + [",".join(r) for r in rows]
    return ("\n".join(lines) + "\n").encode("utf-16")


def make_zip(path):
    base = "GB1900_final_raw_dump_july_2018/"
    locations = [
        ["p1", "P.H.", "u1", "16", "3", "t", "t", ewkb(51.401, -1.320)],  # Newbury
        ["p2", "Cheap Street", "u1", "16", "3", "t", "t", ewkb(51.399, -1.321)],
        ["p3", "Edinburgh", "u2", "16", "3", "t", "t", ewkb(55.95, -3.19)],  # outside the box
    ] + [[f"x{i}", f"Field {i:02d}", "u1", "16", "1", "t", "t", ewkb(51.40, -1.30)]
         for i in range(30)]  # fmt: skip
    transcriptions = [
        ["a", "p1", "P.H.", "", "u1", "t", "t"],
        ["b", "p1", "P.H.", "", "u2", "t", "t"],
        ["c", "p1", "PH", "", "u3", "t", "t"],
        ["d", "p2", "Cheap St.", "", "u1", "t", "t"],
        ["e", "p2", "Cheap Street", "", "u2", "t", "t"],
    ]
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(base + "gb1900_locations.csv", utf16_csv(
            ["pin_id", "first_transcription", "user_id", "zoom_level", "classification_count",
             "created_timestamp", "updated_timestamp", "g_point_wgs"], locations))  # fmt: skip
        zf.writestr(base + "gb1900_transcriptions.csv", utf16_csv(
            ["transcription_id", "pin_id", "transcription", "comment", "user_id",
             "created_timestamp", "updated_timestamp"], transcriptions))  # fmt: skip


@pytest.fixture
def imported(tmp_path):
    load_all()
    path = tmp_path / "dump.zip"
    make_zip(path)
    call_command("import_old_map_names", zip=str(path), pilot=True, stdout=io.StringIO())
    return Dataset.objects.get(key="old-map-names")


# --- Wikidata canned responses -----------------------------------------------------

SEARCH = {
    "search": [
        {"id": "Q1", "label": "Newbury", "description": "town in Berkshire"},
        {"id": "Q2", "label": "Newbury Racecourse", "description": "racecourse"},
    ],
    "search-continue": 2,
}
SEARCH_2 = {"search": [{"id": "Q3", "label": "Newbury Abbey", "description": "abbey"}]}
ENTITY = {
    "entities": {
        "Q1": {
            "labels": {"en": {"value": "Newbury"}},
            "descriptions": {"en": {"value": "town in Berkshire"}},
            "claims": {
                "P625": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"latitude": 51.4, "longitude": -1.32}}}}],
                "P31": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"id": "Q3957"}}}}],
            },
            "sitelinks": {"enwiki": {"url": "https://en.wikipedia.org/wiki/Newbury,_Berkshire"}},
        }
    }
}  # fmt: skip


@pytest.fixture
def wikidata(monkeypatch):
    def fake(url, params, timeout=10.0):
        if params["action"] == "wbsearchentities":
            return SEARCH if int(params["continue"]) == 0 else SEARCH_2
        ids = params["ids"]
        return ENTITY if ids == "Q1" else {"entities": {ids: {"id": ids, "missing": ""}}}

    monkeypatch.setattr(sources, "http_get_json", fake)
    return WikidataConnector()


# --- The contract ------------------------------------------------------------------


@pytest.fixture(params=["checked-reference", "old-map-names", "wikidata"])
def connector_case(request, imported, wikidata):
    return {
        "checked-reference": (ReferenceConnector(), "Cheap Street", "pubwiki-pigeons"),
        "old-map-names": (OldMapNamesConnector(), "", "p1"),
        "wikidata": (wikidata, "Newbury", "Q1"),
    }[request.param]


def test_contract_search_and_record(connector_case):
    connector, query, known_id = connector_case
    assert connector.key in CONNECTORS
    page = connector.search(query, page_size=2)
    assert page.records, "search returns records"
    for r in page.records:
        assert r.connector == connector.key and r.id and r.title
    record = connector.get_record(known_id)
    assert record.id == known_id and record.title
    assert connector.citation(record)
    assert connector.storage_policy(record) in {"full_copy", "metadata_only", "reference_only"}


def test_contract_pagination_has_no_repeats(connector_case):
    connector, query, _ = connector_case
    seen, cursor, pages = [], None, 0
    while pages < 50:
        page = connector.search(query, cursor=cursor, page_size=2)
        seen += [r.id for r in page.records]
        pages += 1
        if not page.next_cursor:
            break
        cursor = page.next_cursor
    assert pages > 1, "pagination happened"
    assert len(seen) == len(set(seen)), "no record appears twice"


def test_contract_unknown_record_and_bad_cursor(connector_case):
    connector, query, _ = connector_case
    with pytest.raises(NotFound):
        connector.get_record("Q999999999" if connector.key == "wikidata" else "no-such-id")
    with pytest.raises(BadQuery):
        connector.search(query or "a", cursor="!!!not-a-cursor")


@pytest.mark.parametrize(
    "failure, expected",
    [
        (urllib.error.HTTPError("u", 429, "Too Many", {}, None), RateLimited),
        (urllib.error.HTTPError("u", 403, "Forbidden", {}, None), AccessDenied),
        (urllib.error.HTTPError("u", 502, "Bad Gateway", {}, None), Unavailable),
        (urllib.error.URLError("down"), Unavailable),
        (TimeoutError("slow"), Unavailable),
    ],
)
def test_live_api_failures_map_to_clear_errors(monkeypatch, failure, expected):
    def boom(*args, **kwargs):
        raise failure

    monkeypatch.setattr(sources.urllib.request, "urlopen", boom)
    with pytest.raises(expected):
        WikidataConnector().search("Newbury")


def test_wikidata_sends_a_descriptive_user_agent(monkeypatch):
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"search": []}'

    def capture(request, timeout, context=None):
        seen["ua"] = request.get_header("User-agent")
        seen["context"] = context
        return Response()

    monkeypatch.setattr(sources.urllib.request, "urlopen", capture)
    WikidataConnector().search("Newbury")
    assert seen["ua"].startswith("ArchiveHubBot/") and "github.com/Discern-AI" in seen["ua"]
    # Full certificate verification through the OS trust store, never disabled.
    assert seen["context"] is sources._TLS
    assert seen["context"].verify_mode == ssl.CERT_REQUIRED and seen["context"].check_hostname


def test_wikidata_record_details(wikidata):
    r = wikidata.get_record("Q1")
    assert (r.latitude, r.longitude) == (51.4, -1.32)
    assert r.fields["wikipedia"].startswith("https://en.wikipedia.org/")


def test_hosted_dataset_missing_is_unavailable(db):
    with pytest.raises(Unavailable):
        OldMapNamesConnector().search("x")


# --- The GB1900 import -------------------------------------------------------------


def test_ewkb_point_parsing():
    assert parse_ewkb_point(ewkb(51.4, -1.32)) == pytest.approx((51.4, -1.32))
    assert parse_ewkb_point("zz") is None


def test_best_reading_prefers_agreement():
    pin = Pin(0, 0, "Cheap St.")
    pin.readings.update({"Cheap St.": 1, "Cheap Street": 2})
    assert best_reading(pin) == ("Cheap Street", ["Cheap St."], 3)


def test_import_keeps_the_box_and_the_agreed_reading(imported):
    assert imported.import_scope == "Newbury and West Berkshire"
    assert imported.licence == "CC0 1.0"
    assert len(imported.original_sha256) == 64
    titles = set(DatasetRow.objects.values_list("title", flat=True))
    assert "Edinburgh" not in titles
    ph = DatasetRow.objects.get(external_id="p1")
    assert ph.title == "P.H." and ph.fields == {"variants": ["PH"], "transcriptions": 3}
    assert "user" not in str(ph.fields)  # contributor IDs are not kept
    assert "GB1900" not in OldMapNamesConnector.name  # licence: derived work can't use the name


def test_import_is_repeatable(imported, tmp_path):
    before = imported.rows.count()
    path = tmp_path / "again.zip"
    make_zip(path)
    call_command("import_old_map_names", zip=str(path), pilot=True, stdout=io.StringIO())
    assert Dataset.objects.get(key="old-map-names").rows.count() == before


def test_import_covers_great_britain_by_default(tmp_path):
    load_all()
    path = tmp_path / "dump.zip"
    make_zip(path)
    call_command("import_old_map_names", zip=str(path), stdout=io.StringIO())
    dataset = Dataset.objects.get(key="old-map-names")
    assert dataset.import_scope == "Great Britain"
    assert DatasetRow.objects.filter(dataset=dataset, title="Edinburgh").exists()
