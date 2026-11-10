"""Time map: public and private items stay apart, and private items stay private."""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.test import Client
from django.utils import timezone

from archive.models import FileAsset
from conftest import make_user
from connectors.models import Dataset, DatasetRow
from core.models import AuditLog
from history.loader import load_all
from history.models import Assertion, Organisation, Place, Source
from interviews.models import InterviewSession, Segment
from projects.models import Chat, Project, ProjectMember, Role
from timemap.models import MapItem
from timemap.queries import BBox, overlaps

pytestmark = pytest.mark.django_db
JSON = "application/json"
# Central Newbury, about 1.5 km across.
NEWBURY = "-1.335,51.392,-1.305,51.408"


@pytest.fixture
def ref(db):
    load_all()


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, title="Gran's Newbury")


def features(client, **params):
    params.setdefault("bbox", NEWBURY)
    return client.get("/api/v1/map/features", params).json()


def add_memory(client, project, **kw):
    body = {
        "kind": "memory",
        "title": "Gran's first job",
        "text": "She served at the Pigeons on Saturdays.",
        "latitude": 51.4004,
        "longitude": -1.3231,
        "year_from": 1952,
        "year_to": 1952,
        **kw,
    }
    return client.post(f"/api/v1/projects/{project.id}/map-items", body, content_type=JSON)


def test_reference_places_carry_their_location_source(ref):
    cheap = Place.objects.get(key="cheap-street")
    assert cheap.latitude is not None and cheap.geocode_precision == "street"
    assert "CHEAP STREET" in cheap.geocode_source
    # Not on the c.1900 map names, so it isn't placed rather than guessed.
    assert Place.objects.get(key="st-marys-hill").latitude is None


def test_layers_without_a_key_say_historic_maps_are_off(alice_client, settings):
    settings.MAPTILER_KEY = ""
    data = alice_client.get("/api/v1/map/layers").json()
    assert data["today"]["style"].startswith("https://tiles.openfreemap.org/")
    assert all(not layer["available"] for layer in data["historic"])
    assert all("tilejson" not in layer for layer in data["historic"])


def test_layers_with_a_key(alice_client, settings):
    settings.MAPTILER_KEY = "abc"
    six_inch = alice_client.get("/api/v1/map/layers").json()["historic"][0]
    assert six_inch["available"] and six_inch["years"] == [1888, 1913]
    assert six_inch["tilejson"].endswith("uk-osgb10k1888/tiles.json?key=abc")
    assert "National Library of Scotland" in six_inch["attribution"]


def test_map_needs_login():
    assert Client().get("/api/v1/map/features", {"bbox": NEWBURY}).status_code == 401


def test_bad_area_and_years(alice_client):
    url = "/api/v1/map/features"
    assert alice_client.get(url, {"bbox": "1,2,3"}).status_code == 422
    assert alice_client.get(url, {"bbox": "5,0,1,1"}).status_code == 422
    assert alice_client.get(url, {"bbox": NEWBURY, "year_from": 9999}).status_code == 422


def test_overlaps():
    assert overlaps(1851, 1940, 1900, 1900)
    assert not overlaps(1851, 1940, 1950, 1960)
    assert overlaps(1911, None, 1910, 1920)
    assert not overlaps(None, None, 1900, 1910)  # undated never matches a year
    assert overlaps(None, None, None, None)


def test_public_records_and_claims_by_year(ref, alice_client):
    in_1900 = features(alice_client, year_from=1895, year_to=1905)
    titles = [f["title"] for f in in_1900["public"]]
    assert any("Pigeons, 5 Cheap Street" in t for t in titles)  # covers 1851–1940
    assert all(f["layer"] == "public" for f in in_1900["public"])
    assert in_1900["private"] == []
    record = next(f for f in in_1900["public"] if f["kind"] == "record")
    assert record["date_role"] == "record_covers" and record["url"].startswith("https://")
    assert record["precision"] == "street"

    in_1970 = features(alice_client, year_from=1970, year_to=1970)
    assert not any("Pigeons, 5 Cheap Street" in f["title"] for f in in_1970["public"])
    assert any("1970" in f["title"] for f in in_1970["public"])


def test_dated_claims_show_as_events(ref, alice_client):
    data = features(alice_client, year_from=1851, year_to=1851)
    claim = next(f for f in data["public"] if f["kind"] == "claim")
    assert claim["date_role"] == "event" and claim["title"].startswith("The Pigeons")


def test_a_photo_date_is_when_it_was_taken(ref, alice_client):
    data = features(alice_client, year_from=1908, year_to=1908)
    photo = next(f for f in data["public"] if "photographed" in f["title"])
    assert photo["date_role"] == "made"


def test_undated_items_only_when_asked(ref, alice_client):
    plain = features(alice_client, year_from=1800, year_to=2000)
    assert all(f["date_role"] != "undated" for f in plain["public"])
    with_undated = features(alice_client, year_from=1800, year_to=2000, undated=True)
    undated = [f for f in with_undated["public"] if f["date_role"] == "undated"]
    assert undated  # e.g. the 69 Cheap Street claim has no date


def test_claims_about_people_are_not_mapped(ref, alice, alice_client):
    from history.models import Person

    person = Person.objects.create(name="Living Person", living_status="living")
    Assertion.objects.create(
        subject_type=ContentType.objects.get_for_model(Person),
        subject_id=person.id,
        predicate="lived at",
        value="Cheap Street",
        year_from=1990,
    )
    data = features(alice_client, year_from=1980, year_to=2000)
    assert not any("Living Person" in f["title"] for f in data["public"] + data["private"])


def test_old_map_names_only_for_c1900_and_when_zoomed_in(ref, alice_client):
    ds = Dataset.objects.create(
        key="old-map-names", name="Old map names", source=Source.objects.get(key="gb1900")
    )
    DatasetRow.objects.create(
        dataset=ds,
        external_id="x1",
        title="CHEAP STREET",
        title_lower="cheap street",
        latitude=51.4005,
        longitude=-1.3231,
    )
    near = features(alice_client, year_from=1900, year_to=1900)
    assert [n["title"] for n in near["map_names"]] == ["CHEAP STREET"]
    assert near["map_names"][0]["date_role"] == "map_survey"
    assert features(alice_client, year_from=1960, year_to=1960)["map_names"] == []
    wide = features(alice_client, bbox="-2,51,-1,52", year_from=1900, year_to=1900)
    assert wide["map_names"] == [] and any("Zoom in" in n for n in wide["notes"])


def test_memory_is_private_to_the_project(ref, alice_client, bob_client, project):
    r = add_memory(alice_client, project)
    assert r.status_code == 201
    item = r.json()
    assert item["layer"] == "private" and item["date_role"] == "event"
    assert item["project_title"] == "Gran's Newbury"

    mine = features(alice_client, year_from=1950, year_to=1955)
    assert [f["title"] for f in mine["private"]] == ["Gran's first job"]
    theirs = features(bob_client, year_from=1950, year_to=1955)
    assert theirs["private"] == []
    assert not any("Gran" in f["title"] for f in theirs["public"])
    # Bob can't see, change or delete it.
    assert bob_client.get(f"/api/v1/projects/{project.id}/map-items").status_code == 404
    item_url = f"/api/v1/map-items/{item['extra']['item_id']}"
    assert bob_client.patch(item_url, {"title": "x"}, content_type=JSON).status_code == 404
    assert bob_client.delete(item_url).status_code == 404
    assert "map_item.create" in AuditLog.objects.values_list("action", flat=True)


def test_viewers_see_but_cannot_add(ref, alice_client, bob, bob_client, project):
    ProjectMember.objects.create(project=project, user=bob, role=Role.VIEWER)
    add_memory(alice_client, project)
    assert len(features(bob_client, year_from=1950, year_to=1955)["private"]) == 1
    assert add_memory(bob_client, project).status_code == 404


def test_memory_needs_words_and_a_place_on_the_map(alice_client, project):
    assert add_memory(alice_client, project, text="  ").status_code == 422
    assert add_memory(alice_client, project, title="").status_code == 422
    assert add_memory(alice_client, project, latitude=95).status_code == 422


def test_photo_must_be_an_image_from_the_same_project(alice, alice_client, project):
    other = Project.objects.create(owner=alice, title="Other")

    def make_file(p, kind):
        return FileAsset.objects.create(
            project=p,
            name="f",
            original=ContentFile(b"x", name="f"),
            size=1,
            sha256="0" * 64,
            kind=kind,
            content_type="image/png",
        )

    photo, elsewhere, pdf = (
        make_file(project, "image"),
        make_file(other, "image"),
        make_file(project, "pdf"),
    )
    base = {"kind": "photo", "text": ""}
    assert add_memory(alice_client, project, **base).status_code == 422
    assert add_memory(alice_client, project, **base, file_id=str(elsewhere.id)).status_code == 422
    assert add_memory(alice_client, project, **base, file_id=str(pdf.id)).status_code == 422
    r = add_memory(alice_client, project, **base, file_id=str(photo.id), date_role="made")
    assert r.status_code == 201
    assert r.json()["date_role"] == "made"
    assert r.json()["link"] == f"/archive?project={project.id}&file={photo.id}"


def test_interview_passage_links_real_lines(alice, alice_client, project):
    chat = Chat.objects.create(owner=alice, project=project)
    session = InterviewSession.objects.create(
        chat=chat,
        narrator="Gran",
        consent_confirmed_by=alice,
        consent_confirmed_at=timezone.now(),
        consent_notice="notice",
    )
    Segment.objects.create(
        session=session, line=1, start_ms=0, end_ms=10, text="The Pigeons", speaker="Gran",
        engine="fake",
    )  # fmt: skip
    base = {"kind": "interview", "text": "", "interview_id": str(session.id)}
    assert add_memory(alice_client, project, **base, lines=[7]).status_code == 422
    r = add_memory(alice_client, project, **base, lines=[1])
    assert r.status_code == 201 and r.json()["link"] == f"/interviews/{session.id}"


def test_edit_and_delete_own_item(alice_client, project):
    item = add_memory(alice_client, project).json()
    url = f"/api/v1/map-items/{item['extra']['item_id']}"
    r = alice_client.patch(url, {"year_from": 1950, "year_to": 1955}, content_type=JSON)
    assert r.json()["date_display"] == "1950–1955"
    assert alice_client.delete(url).status_code == 204
    assert not MapItem.objects.exists()


def test_private_project_claims_are_private(ref, alice, alice_client, bob_client, project):
    pigeons = Organisation.objects.get(key="pigeons")
    Assertion.objects.create(
        subject_type=ContentType.objects.get_for_model(Organisation),
        subject_id=pigeons.id,
        predicate="family story",
        value="Grandad drank here",
        year_from=1960,
        year_to=1960,
        project=project,
        method="user",
    )
    mine = features(alice_client, year_from=1960, year_to=1960)
    assert any("Grandad" in f["title"] for f in mine["private"])
    assert not any("Grandad" in f["title"] for f in mine["public"])
    theirs = features(bob_client, year_from=1960, year_to=1960)
    assert not any("Grandad" in f["title"] for f in theirs["public"] + theirs["private"])


def test_places_list_starts_with_cheap_street(ref, alice_client):
    places = alice_client.get("/api/v1/map/places").json()
    assert places[0]["key"] == "cheap-street" and places[0]["geocode_source"]
    assert all(p["latitude"] is not None for p in places)
    assert alice_client.get("/api/v1/map/places", {"q": "greenham"}).json()[0]["key"] == (
        "greenham-road"
    )


def test_bbox_contains():
    box = BBox.parse(NEWBURY)
    assert box.contains(51.4, -1.32) and not box.contains(52, -1.32) and box.small


def test_what_else_is_known_here(ref, alice, alice_client, project, monkeypatch):
    from connectors.base import ConnectorRecord, Page
    from connectors.sources import get_connector

    ds = Dataset.objects.create(
        key="old-map-names", name="Old map names", source=Source.objects.get(key="gb1900")
    )
    DatasetRow.objects.create(
        dataset=ds, external_id="n1", title="Corn Exchange", title_lower="corn exchange",
        latitude=51.3990, longitude=-1.3214,
    )  # fmt: skip
    DatasetRow.objects.create(
        dataset=ds, external_id="n2", title="P.H.", title_lower="p.h.",
        latitude=51.3986, longitude=-1.3216,
    )  # fmt: skip
    DatasetRow.objects.create(
        dataset=ds, external_id="far", title="Far away", title_lower="far away",
        latitude=51.41, longitude=-1.3214,
    )  # fmt: skip
    pigeons = Organisation.objects.get(key="pigeons")
    Assertion.objects.create(
        subject_type=ContentType.objects.get_for_model(Organisation), subject_id=pigeons.id,
        predicate="family story", value="Grandad drank here", project=project, method="user",
    )  # fmt: skip
    sent = []

    def gazette(query, cursor=None, page_size=25):
        sent.append(query)
        record = ConnectorRecord(
            connector="the-gazette", id="London/issue/25693/page/2224",
            title="The London Gazette, Issue 25693, Page 2224", date_text="1887-04-19",
            url="https://www.thegazette.co.uk/London/issue/25693/page/2224",
        )  # fmt: skip
        return Page(records=[record], searched=f"The Gazette for {query}")

    monkeypatch.setattr(get_connector("the-gazette"), "search", gazette)
    url = "/api/v1/map/nearby"
    here = {"lat": 51.3984, "lng": -1.3214, "name": "No. 6 CHEAP STREET"}
    data = alice_client.get(url, here).json()
    assert data["street"] == "Cheap Street, Newbury"
    assert [n["title"] for n in data["map_names"]] == ["P.H.", "Corn Exchange"]  # nearest first
    assert data["map_names"][0]["meaning"] == "public house"
    assert data["map_names"][0]["meaning_source"] == "https://maps.nls.uk/os/abbrev/p.html"
    assert any("Pigeons, 5 Cheap Street" in f["title"] for f in data["public"])
    assert [f["title"] for f in data["private"]] == ["The Pigeons: family story Grandad drank here"]
    assert sent == ['"Cheap Street" Newbury']  # only the street, never anything of the user's
    assert data["gazette"]["results"][0]["date"] == "1887-04-19"
    assert any("may be about any building" in n for n in data["notes"])

    # Someone else sees the public evidence but not this project's claim.
    other = Client()
    other.force_login(make_user("carol@example.com"))
    assert other.get(url, here).json()["private"] == []

    nowhere = alice_client.get(url, {"lat": 51.3984, "lng": -1.3214, "name": "Some House"}).json()
    assert nowhere["street"] is None and nowhere["gazette"] is None
    assert alice_client.get(url, {"lat": 95, "lng": 0}).status_code == 422


def test_protected_areas_are_live_cached_and_labelled(alice_client, monkeypatch):
    from django.core.cache import cache

    from connectors.base import Unavailable
    from timemap import areas

    cache.clear()
    seen = []
    square = {
        "type": "Polygon",
        "coordinates": [[[-1.33, 51.39], [-1.32, 51.39], [-1.32, 51.40], [-1.33, 51.39]]],
    }

    def fake(url, params, timeout=10.0, headers=None):
        seen.append(url)
        if "/8/" in url:
            raise Unavailable("down")
        if "Conservation_Areas" in url:
            props = {
                "UID": 1957,
                "NAME": "Newbury Town Centre",
                "DATE_OF_DE": "03/1971",
                "LPA": "West Berkshire",
            }
        else:
            props = {"ListEntry": 1, "Name": "Donnington Castle", "SchedDate": -1420070400000,
                     "hyperlink": "https://historicengland.org.uk/listing/the-list/list-entry/1"}  # fmt: skip
        return {"features": [{"geometry": square, "properties": props}]}

    monkeypatch.setattr(areas, "http_get_json", fake)
    data = alice_client.get("/api/v1/map/areas", {"bbox": NEWBURY}).json()
    names = {f["properties"]["name"]: f["properties"] for f in data["features"]}
    assert names["Newbury Town Centre"]["designated"] == "1971"
    assert names["Newbury Town Centre"]["label"] == "Conservation area"
    monument = next(
        f["properties"] for f in data["features"] if f["properties"]["kind"] == "scheduled_monument"
    )
    assert monument["designated"] == "1925" and monument["url"]
    assert any("battlefields couldn't be loaded" in n.lower() for n in data["notes"])
    assert "Open Government Licence" in data["attribution"]
    # A failed layer isn't cached, so the next look tries again.
    alice_client.get("/api/v1/map/areas", {"bbox": NEWBURY})
    assert len(seen) == 8
    wide = alice_client.get("/api/v1/map/areas", {"bbox": "-3,50,-1,52"}).json()
    assert wide["features"] == [] and "Zoom in" in wide["notes"][0]
    assert alice_client.get("/api/v1/map/areas", {"bbox": "x"}).status_code == 422


def test_go_to_any_place(ref, alice_client, settings):
    ds = Dataset.objects.create(
        key="old-map-names", name="Old map names", source=Source.objects.get(key="gb1900")
    )
    for n, (title, lat) in enumerate(
        (("EDINBURGH", 55.95), ("Edinburgh Road", 51.5), ("EDINBURGHSHIRE", 55.9))
    ):
        DatasetRow.objects.create(dataset=ds, external_id=f"e{n}", title=title,
                                  title_lower=title.lower(), latitude=lat, longitude=-3.19)  # fmt: skip
    settings.GEONAMES_USERNAME = ""
    found = alice_client.get("/api/v1/map/places", {"q": "Edinburgh"}).json()
    assert found[0]["name"] == "Edinburgh" and found[0]["kind"] == "town"
    assert found[0]["latitude"] == 55.95 and "c.1900" in found[0]["geocode_source"]
    assert [f["name"] for f in found][1:] == ["Edinburghshire", "Edinburgh Road"]
    # Our own places still come first.
    assert alice_client.get("/api/v1/map/places", {"q": "Cheap"}).json()[0]["key"] == "cheap-street"


def test_what_is_here_outside_our_places(ref, alice_client, monkeypatch, settings):
    from connectors.base import Page
    from connectors.sources import get_connector
    from timemap.nearby import street_from_name

    assert street_from_name("8, CHEAP STREET") == "Cheap Street"
    assert street_from_name("12 and 14 HIGH STREET") == "High Street"
    assert street_from_name("Barn at Manor Farm, Church Lane") == "Church Lane"
    assert street_from_name("THE OLD RECTORY") == ""

    sent = []
    monkeypatch.setattr(
        get_connector("the-gazette"),
        "search",
        lambda query, cursor=None, page_size=25: sent.append(query) or Page(records=[]),
    )
    settings.GEONAMES_USERNAME = ""
    url = "/api/v1/map/nearby"
    york = {"lat": 53.959, "lng": -1.081, "name": "23, STONEGATE STREET"}
    data = alice_client.get(url, york).json()
    assert data["gazette"] is None and sent == []  # no town known: don't guess
    assert any("can't tell which town" in n for n in data["notes"])

    settings.GEONAMES_USERNAME = "geo-user"
    monkeypatch.setattr(get_connector("geonames"), "nearest_place", lambda lat, lng: "York")
    data = alice_client.get(url, york).json()
    assert sent == ['"Stonegate Street" York']
    assert any("with York" in n for n in data["notes"])


@pytest.fixture
def three_lists(monkeypatch):
    """England, Scotland and Wales answer from stand-ins; returns the requests made."""
    from django.core.cache import cache

    from timemap import listed

    cache.clear()
    seen = []

    def fake(url, params, timeout=10.0, headers=None):
        seen.append((url, params))
        if url == listed.ENGLAND:
            return {
                "features": [{
                    "attributes": {"ListEntry": 1220923, "Name": "No. 6 CHEAP STREET", "Grade": "II",
                                   "ListDate": 431308800000,
                                   "hyperlink": "https://historicengland.org.uk/listing/the-list/list-entry/1220923"},
                    "geometry": {"points": [[-1.3214, 51.3984]]},
                }],
                "exceededTransferLimit": True,
            }  # fmt: skip
        if url == listed.SCOTLAND:
            point = {"attributes": {"DES_REF": "LB3006", "DES_TITLE": "12-16 BANK STREET", "CATEGORY": "B",
                                    "DESIGNATED": 156038400000,
                                    "LINK": "https://portal.historicenvironment.scot/designation/LB3006"},
                     "geometry": {"x": -3.1931, "y": 55.9498}}  # fmt: skip
            return {"features": [point, point]}  # one building, two points
        return {
            "features": [{
                "properties": {"RecordNumber": 13662, "Name": "Cardiff Castle", "Grade": "I",
                               "DesignationDate": "1952-02-12T00:00:00Z",
                               "Report": "http://cadwpublic-api.azurewebsites.net/reports/x"},
                "geometry": {"type": "MultiPoint", "coordinates": [[-3.1822, 51.4817]]},
            }]
        }  # fmt: skip

    monkeypatch.setattr(listed, "http_get_json", fake)
    return seen


def test_listed_buildings_from_all_three_lists(ref, alice_client, three_lists):
    from timemap import listed

    assert features(alice_client)["listed_buildings"] == []  # off unless asked
    data = features(alice_client, listed="true", year_from=1850, year_to=1860)
    by_nation = {b["extra"]["nation"]: b for b in data["listed_buildings"]}
    england, scotland, wales = by_nation["england"], by_nation["scotland"], by_nation["wales"]
    assert england["date_role"] == "listed" and england["date_display"] == "1983"
    assert (
        england["summary"] == "Grade II listed building"
        and england["extra"]["record_id"] == "1220923"
    )
    assert (
        scotland["summary"] == "Category B listed building" and scotland["date_display"] == "1974"
    )
    assert "connector" not in scotland["extra"]  # nothing to save it with yet
    assert wales["title"] == "Cardiff Castle" and wales["date_display"] == "1952"
    assert "Cadw" in wales["source"] and "Open Government Licence" in wales["extra"]["credit"]
    assert sum(1 for b in data["listed_buildings"] if b["extra"]["nation"] == "scotland") == 1
    assert any("Showing up to 300" in n for n in data["notes"])
    wales_bbox = next(p for u, p in three_lists if u == listed.WALES)["bbox"]
    assert wales_bbox.endswith(",CRS:84") and wales_bbox.startswith("-1.335")
    before = len(three_lists)
    features(alice_client, listed="true", year_from=1900, year_to=1910)
    assert len(three_lists) == before  # same area: cached, whatever the year
    wide = features(alice_client, bbox="-2,51,-1,52", listed="true")
    assert wide["listed_buildings"] == [] and any(
        "Zoom in to see listed" in n for n in wide["notes"]
    )


def test_one_list_down_is_said_plainly(ref, alice_client, three_lists, monkeypatch):
    from connectors.base import Unavailable
    from timemap import listed

    real = listed.http_get_json

    def scotland_down(url, params, timeout=10.0, headers=None):
        if url == listed.SCOTLAND:
            raise Unavailable("down")
        return real(url, params, timeout=timeout, headers=headers)

    monkeypatch.setattr(listed, "http_get_json", scotland_down)
    data = features(alice_client, listed="true")
    nations = {b["extra"]["nation"] for b in data["listed_buildings"]}
    assert nations == {"england", "wales"}
    assert any("Historic Environment Scotland couldn't be loaded" in n for n in data["notes"])


BELFAST = "-5.935,54.590,-5.920,54.600"


def _ni_geojson(tmp_path):
    import json

    def building(ref, grade, x, y, address="St Malachy's Church\n24 Alfred Street\nBelfast"):
        return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [x, y]},
                "properties": {"HB_ref": ref, "CurrentGra": grade, "Address": address,
                               "Date_Const": "1840 - 1859", "Townland": "Town Parks",
                               "Council": "Belfast", "CurrentUse": "Church"}}  # fmt: skip

    data = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:29902"}},
        "features": [
            building("HB26/30/023 A", "A", 334051.4509, 373755.7695),
            building("HB26/30/999", "Record Only", 334060.0, 373760.0),  # not listed
            building("HB26/30/998", "Delisted", 334070.0, 373770.0),
            {"type": "Feature", "geometry": None, "properties": {"HB_ref": "HB1", "CurrentGra": "A"}},
        ],
    }  # fmt: skip
    path = tmp_path / "hb.geojson"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_northern_ireland_listed_buildings_from_the_import(
    ref, alice_client, three_lists, tmp_path
):
    from django.core.management import call_command

    before = features(alice_client, bbox=BELFAST, listed="true")
    assert any(
        "Northern Ireland's listed buildings haven't been loaded" in n for n in before["notes"]
    )

    call_command("import_ni_listed_buildings", file=str(_ni_geojson(tmp_path)))
    row = DatasetRow.objects.get(dataset__key="ni-listed-buildings")
    assert row.external_id == "HB26/30/023 A" and row.title == "St Malachy's Church"
    # Irish Grid converted to the same place DfC's own service gives.
    assert abs(row.latitude - 54.594262) < 1e-5 and abs(row.longitude + 5.926802) < 1e-5

    from django.core.cache import cache

    cache.clear()
    data = features(alice_client, bbox=BELFAST, listed="true")
    ni = [b for b in data["listed_buildings"] if b["extra"]["nation"] == "northern_ireland"]
    assert len(ni) == 1
    b = ni[0]
    assert b["summary"] == "Grade A listed building (HB26/30/023 A)"
    assert b["date_role"] == "built" and b["date_display"] == "1840 - 1859"
    assert "Open Data NI" in b["extra"]["credit"] and "Department for Communities" in b["source"]
    assert b["extra"]["address"] == "St Malachy's Church, 24 Alfred Street, Belfast"
    assert not any("haven't been loaded" in n for n in data["notes"])
    # Away from Northern Ireland nothing is said about it.
    cache.clear()
    assert not any("Northern Ireland" in n for n in features(alice_client, listed="true")["notes"])


def test_ni_import_refuses_other_coordinates(ref, tmp_path):
    import json

    from django.core.management import CommandError, call_command

    path = tmp_path / "wgs.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    with pytest.raises(CommandError, match="Irish Grid"):
        call_command("import_ni_listed_buildings", file=str(path))


def test_protected_areas_in_scotland_and_wales_from_their_own_services(alice_client, monkeypatch):
    from django.core.cache import cache

    from timemap import areas

    cache.clear()
    seen = []
    shape = {"type": "Polygon", "coordinates": [[[-3.2, 55.95], [-3.19, 55.95], [-3.19, 55.96], [-3.2, 55.95]]]}  # fmt: skip

    def fake(url, params, timeout=10.0, headers=None):
        seen.append((url, params))
        if url.startswith(areas.HES):
            props = {"DES_REF": "SM90", "DES_TITLE": "CULLODEN MUIR", "DESIGNATED": 0,
                     "LINK": "https://portal.historicenvironment.scot/designation/SM90",
                     "LOCAL_AUTH": "Highland"}  # fmt: skip
        else:
            props = {"SAMNumber": "GM427", "Name": "Cooking Mound", "DesignationDate": "1983-03-01T00:00:00Z",
                     "Report": "http://cadwpublic-api.azurewebsites.net/reports/sam/FullReport?id=221",
                     "UnitaryAuthority": "Cardiff", "sitename": "Pierhead",
                     "designation_date": "1984-06-01"}  # fmt: skip
        return {"features": [{"geometry": shape, "properties": props}]}

    monkeypatch.setattr(areas, "http_get_json", fake)
    scot = alice_client.get("/api/v1/map/areas", {"bbox": "-3.22,55.94,-3.16,55.97"}).json()
    assert {u for u, _ in seen} == {
        layer.url for layer in areas.LAYERS if layer.nation == "scotland"
    }
    assert all("resultRecordCount" not in p for _, p in seen)  # HES doesn't page
    first = scot["features"][0]["properties"]
    assert first["name"] == "Culloden Muir" and first["designated"] == "1970"
    assert first["nation"] == "scotland" and first["authority"] == "Highland"
    assert "SC045925" in scot["attribution"] and "Historic England" not in scot["attribution"]

    seen.clear()
    wales = alice_client.get("/api/v1/map/areas", {"bbox": "-4.10,52.40,-4.05,52.43"}).json()
    assert {u for u, _ in seen} == {areas.WALES_WFS}
    assert {p["typeNames"] for _, p in seen} == {
        layer.url for layer in areas.LAYERS if layer.nation == "wales"
    }
    by_kind = {f["properties"]["kind"]: f["properties"] for f in wales["features"]}
    assert by_kind["scheduled_monument"]["designated"] == "1983"
    assert by_kind["conservation_area"]["designated"] == "1984"
    assert "Cadw" in wales["attribution"]

    seen.clear()
    belfast = alice_client.get("/api/v1/map/areas", {"bbox": "-5.95,54.58,-5.90,54.61"}).json()
    assert seen == [] and belfast["features"] == []
    assert belfast["notes"] == ["Northern Ireland's protected areas aren't connected yet."]
