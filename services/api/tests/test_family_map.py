"""Family trees on the time map: suggested locations a person checks, living people never shown.

Uses the synthetic tree in fixtures/illustrative/sample_family.ged (fictional people).
"""

from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from connectors.models import Dataset, DatasetRow
from history.loader import load_all
from history.models import Source
from projects.models import Project, ProjectMember, Role
from timemap.family import suggest, text_key
from timemap.models import PlaceLocation

pytestmark = pytest.mark.django_db
GED = (Path(__file__).parents[3] / "fixtures" / "illustrative" / "sample_family.ged").read_bytes()
JSON = "application/json"
NEWBURY = "-1.335,51.392,-1.305,51.408"
READING = "-1.0,51.44,-0.94,51.47"


@pytest.fixture
def tree(alice, alice_client):
    load_all()  # Newbury has a location from the c.1900 map
    project = Project.objects.create(owner=alice, title="Sample family")
    r = alice_client.post(
        f"/api/v1/projects/{project.id}/files",
        {"file": SimpleUploadedFile("sample_family.ged", GED)},
    )
    file_id = r.json()["id"]
    job = alice_client.post(
        f"/api/v1/files/{file_id}/jobs", {"kind": "gedcom_import"}, content_type=JSON
    ).json()
    assert job["status"] == "done", job
    return project


def places(client, project):
    return client.get(f"/api/v1/projects/{project.id}/family-places").json()


def locate(client, project):
    return client.post(f"/api/v1/projects/{project.id}/family-places/locate")


def private_titles(client, **params):
    params.setdefault("bbox", NEWBURY)
    data = client.get("/api/v1/map/features", params).json()
    return [f["title"] for f in data["private"]], data


def test_places_are_suggested_with_a_source(tree, alice_client):
    before = places(alice_client, tree)
    assert before["places"] == [] and before["not_looked_up"] == 2
    assert locate(alice_client, tree).json() == {"suggested": 1, "not_found": 1}
    listed = {p["text"]: p for p in places(alice_client, tree)["places"]}
    newbury = listed["Newbury, Berkshire, England"]
    assert newbury["status"] == "suggested" and newbury["precision"] == "town"
    assert "NEWBURY" in newbury["source"] and newbury["uses"] == 2
    assert listed["Reading, Berkshire, England"]["status"] == "not_found"
    # Running again doesn't redo or undo anything.
    assert locate(alice_client, tree).json() == {"suggested": 0, "not_found": 0}


def test_family_events_on_the_map_without_living_people(tree, alice_client):
    locate(alice_client, tree)
    titles, data = private_titles(alice_client, year_from=1915, year_to=1925)
    assert titles == ["Birth of Arthur Sample"]
    event = data["private"][0]
    assert event["kind"] == "family_event" and event["layer"] == "private"
    assert event["date_display"] == "ABT 1921" and event["date_role"] == "event"
    assert "location suggested, not yet checked" in event["place"]
    assert event["link"].startswith(f"/projects/{tree.id}/people/")
    # Alice Sample (born 1950 in Newbury, no death) counts as living: never on the map.
    titles, _ = private_titles(alice_client, year_from=1945, year_to=1955)
    assert not any("Alice" in t for t in titles)
    assert data["public"] == [] or all(f["layer"] == "public" for f in data["public"])


def test_family_events_are_private_to_the_project(tree, alice_client, bob, bob_client):
    locate(alice_client, tree)
    titles, _ = private_titles(bob_client, year_from=1915, year_to=1925)
    assert titles == []
    assert bob_client.get(f"/api/v1/projects/{tree.id}/family-places").status_code == 404
    loc = PlaceLocation.objects.get(text__startswith="Newbury")
    body = {"status": "rejected"}
    assert (
        bob_client.patch(f"/api/v1/family-places/{loc.id}", body, content_type=JSON).status_code
        == 404
    )
    ProjectMember.objects.create(project=tree, user=bob, role=Role.VIEWER)
    titles, _ = private_titles(bob_client, year_from=1915, year_to=1925)
    assert titles == ["Birth of Arthur Sample"]  # viewers see it…
    r = bob_client.patch(f"/api/v1/family-places/{loc.id}", body, content_type=JSON)
    assert r.status_code == 404  # …but can't change it


def test_reject_confirm_and_place_by_hand(tree, alice_client):
    locate(alice_client, tree)
    listed = {p["text"]: p for p in places(alice_client, tree)["places"]}
    newbury, reading = listed["Newbury, Berkshire, England"], listed["Reading, Berkshire, England"]
    url = "/api/v1/family-places/"

    r = alice_client.patch(url + newbury["id"], {"status": "rejected"}, content_type=JSON)
    assert r.json()["status"] == "rejected"
    assert private_titles(alice_client, year_from=1915, year_to=1925)[0] == []
    r = alice_client.patch(url + newbury["id"], {"status": "confirmed"}, content_type=JSON)
    assert r.json()["status"] == "confirmed"
    _, data = private_titles(alice_client, year_from=1915, year_to=1925)
    assert "not yet checked" not in data["private"][0]["place"]

    no_location = alice_client.patch(
        url + reading["id"], {"status": "confirmed"}, content_type=JSON
    )
    assert no_location.status_code == 422
    body = {"latitude": 51.4545, "longitude": -0.9781, "precision": "town"}
    r = alice_client.patch(url + reading["id"], body, content_type=JSON)
    assert r.json()["status"] == "confirmed" and r.json()["method"] == "user"
    titles, _ = private_titles(alice_client, bbox=READING, year_from=1985, year_to=1990)
    assert titles == ["Death of Arthur Sample"]
    assert alice_client.patch(url + reading["id"], {}, content_type=JSON).status_code == 422


def test_old_map_names_flag_places_that_share_a_name(db):
    load_all()
    ds = Dataset.objects.create(
        key="old-map-names", name="Old map names", source=Source.objects.get(key="gb1900")
    )
    for n, lat in enumerate((51.40, 51.60)):  # two villages 22 km apart
        DatasetRow.objects.create(
            dataset=ds, external_id=f"x{n}", title="BRADFIELD", title_lower="bradfield",
            latitude=lat, longitude=-1.1,
        )  # fmt: skip
    hit = suggest("Bradfield, Berkshire")
    assert hit["method"] == "old-map-names" and hit["candidates"] == 2
    assert hit["precision"] == "town"
    assert suggest("Nowhere At All") is None


def test_text_key_ignores_case_and_spacing():
    assert text_key("Newbury,  Berkshire") == text_key("newbury , berkshire")
