"""Time map: public and private items stay apart, and private items stay private."""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.test import Client
from django.utils import timezone

from archive.models import FileAsset
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


def test_listed_buildings_layer_is_live_cached_and_opt_in(ref, alice_client, monkeypatch):
    from django.core.cache import cache

    from connectors.sources import get_connector

    cache.clear()
    seen = []
    connector = get_connector("historic-england")

    def fake_query(where, extra):
        seen.append(extra)
        return {
            "features": [
                {
                    "attributes": {
                        "ListEntry": 1220923,
                        "Name": "No. 6 CHEAP STREET",
                        "Grade": "II",
                        "ListDate": 431308800000,
                        "hyperlink": "https://historicengland.org.uk/listing/the-list/list-entry/1220923",
                    },
                    "geometry": {"points": [[-1.3214, 51.3984]]},
                }
            ],
            "exceededTransferLimit": True,
        }

    monkeypatch.setattr(connector, "_query", fake_query)
    assert features(alice_client)["listed_buildings"] == []  # off unless asked
    data = features(alice_client, listed="true", year_from=1850, year_to=1860)
    building = data["listed_buildings"][0]
    assert building["date_role"] == "listed" and building["date_display"] == "1983"
    assert building["layer"] == "public" and building["url"].endswith("1220923")
    assert any("first 300 listed buildings" in n for n in data["notes"])
    assert seen[0]["geometryType"] == "esriGeometryEnvelope"
    features(alice_client, listed="true", year_from=1900, year_to=1910)
    assert len(seen) == 1  # same area: served from the cache, whatever the year
    wide = features(alice_client, bbox="-2,51,-1,52", listed="true")
    assert wide["listed_buildings"] == [] and any(
        "Zoom in to see listed" in n for n in wide["notes"]
    )


def test_listed_buildings_unavailable_is_said_plainly(ref, alice_client, monkeypatch):
    from django.core.cache import cache

    from connectors.base import Unavailable
    from connectors.sources import get_connector

    cache.clear()

    def down(where, extra):
        raise Unavailable("down")

    monkeypatch.setattr(get_connector("historic-england"), "_query", down)
    data = features(alice_client, listed="true")
    assert data["listed_buildings"] == []
    assert any("couldn't be loaded" in n for n in data["notes"])
