"""WP13: lineages (who held a role, one after another) and record orders."""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from archive.models import FileAsset
from genealogy.models import Relationship
from history.loader import load_all
from history.models import Assertion, Organisation, Person
from projects.models import Project

pytestmark = pytest.mark.django_db
JSON = "application/json"


@pytest.fixture
def ref(db):
    load_all()


def person(project, name, born=None, died=None, living="deceased"):
    p = Person.objects.create(project=project, name=name, living_status=living)
    ct = ContentType.objects.get_for_model(Person)
    for pred, y in (("birth date", born), ("death date", died)):
        if y:
            Assertion.objects.create(project=project, subject_type=ct, subject_id=p.id,
                                     predicate=pred, value=str(y), year_from=y, year_to=y,
                                     date_precision="year", status="documented",
                                     method="user")  # fmt: skip
    return p


def test_the_pigeons_licensees_in_order_with_gaps(ref, alice_client):
    subjects = {s["name"]: s for s in alice_client.get("/api/v1/lineages").json()}
    pigeons = subjects["The Pigeons"]
    assert pigeons["roles"] == [{"role": "licensee", "label": "Licensees", "count": 5}]
    r = alice_client.get(f"/api/v1/lineages/organisation/{pigeons['id']}").json()
    assert r["role"] == "licensee" and r["role_label"] == "Licensees"
    names = [h["name"] for h in r["holders"]]
    assert names == ["William Turk", "John H Sambells", "John Spracklen", "Archbld Shute", None]
    last = r["holders"][-1]
    assert last["hidden"] and last["year_from"] == 1940  # may still be living
    assert r["hidden_recent"] == 1 and any("may still be living" in n for n in r["notes"])
    assert {"from": 1882, "to": 1890} in r["gaps"] and {"from": 1929, "to": 1930} in r["gaps"]
    spracklen = r["holders"][2]
    assert (spracklen["year_from"], spracklen["year_to"]) == (1901, 1928)
    assert spracklen["sources"] and spracklen["status"] == "documented"
    assert alice_client.get(f"/api/v1/lineages/organisation/{pigeons['id']}",
                            {"role": "nonsense"}).status_code == 422  # fmt: skip


def test_a_licensee_may_be_someone_in_your_tree(ref, alice, alice_client, bob_client):
    project = Project.objects.create(owner=alice, title="Spracklens")
    match = person(project, "John Spracklen", 1870, 1945)
    person(project, "John Spracklen", 1925, 1990)  # too young to be licensee from 1901
    person(project, "John Spracklen", 1950, living="living")  # living: never matched
    person(project, "Mary Spracklen", 1872, 1950)  # different first name
    pigeons = Organisation.objects.get(key="pigeons")
    r = alice_client.get(f"/api/v1/lineages/organisation/{pigeons.id}").json()
    spracklen = next(h for h in r["holders"] if h["name"] == "John Spracklen")
    assert [c["person_id"] for c in spracklen["connections"]] == [str(match.id)]
    assert "same first name and surname" in spracklen["connections"][0]["reason"]
    # Someone without access to the tree sees no connection.
    other = bob_client.get(f"/api/v1/lineages/organisation/{pigeons.id}").json()
    assert all(h["connections"] == [] for h in other["holders"])


def test_record_offers_follow_the_gro_rules(alice, alice_client):
    project = Project.objects.create(owner=alice, title="Mine")
    arthur = person(project, "Arthur Sample", 1890, 1960)
    edith = person(project, "Edith Fictional", 1892, 1950)
    Relationship.objects.create(project=project, person=arthur, relative=edith, kind="spouse",
                                fields={"marriage_date": "4 JUN 1914", "marriage_place": "Newbury"})  # fmt: skip
    r = alice_client.get(f"/api/v1/projects/{project.id}/people/{arthur.id}/record-offers").json()
    by = {e["event"]: e for e in r["events"]}
    assert {o["key"] for o in by["birth"]["offers"]} == {
        "gro-certificate",
        "gro-pdf",
        "gro-online-view",
    }
    assert {o["key"] for o in by["death"]["offers"]} == {"gro-certificate"}  # PDFs to 1957 only
    assert {o["key"] for o in by["marriage"]["offers"]} == {"gro-certificate"}
    cert = by["birth"]["offers"][0]
    assert cert["total_pence"] == 1250 and cert["route"] == "referral" and cert["checked_on"]
    assert "GRO index reference" in by["birth"]["note"]
    assert "doesn't sell" in r["note"]
    scot = person(project, "Ian Scot", 1880, 1940)
    ct = ContentType.objects.get_for_model(Person)
    Assertion.objects.create(project=project, subject_type=ct, subject_id=scot.id,
                             predicate="birth place", value="Leith, Scotland",
                             status="documented", method="user")  # fmt: skip
    s = alice_client.get(f"/api/v1/projects/{project.id}/people/{scot.id}/record-offers").json()
    birth = next(e for e in s["events"] if e["event"] == "birth")
    assert birth["offers"] == [] and "England and Wales" in birth["note"]
    early = person(project, "Old Timer", 1800, 1850)
    e = alice_client.get(f"/api/v1/projects/{project.id}/people/{early.id}/record-offers").json()
    assert "parish registers" in next(x for x in e["events"] if x["event"] == "birth")["note"]
    young = person(project, "Young One", 1990, living="living")
    y = alice_client.get(f"/api/v1/projects/{project.id}/people/{young.id}/record-offers").json()
    assert y["events"] == [] and "may be living" in y["note"]


def test_an_order_is_tracked_until_the_record_arrives(alice, alice_client, bob_client):
    project = Project.objects.create(owner=alice, title="Mine")
    arthur = person(project, "Arthur Sample", 1890, 1960)
    body = {"project_id": str(project.id), "person_id": str(arthur.id), "offer_key": "gro-pdf",
            "event": "birth"}  # fmt: skip
    r = alice_client.post("/api/v1/record-orders", body, content_type=JSON)
    assert r.status_code == 422 and "index reference" in r.json()["detail"]
    body["index_reference"] = "SAMPLE ARTHUR, Newbury 2c 123"
    r = alice_client.post("/api/v1/record-orders", body, content_type=JSON)
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "planned" and order["total_pence"] == 800
    assert order["fees"] == [{"label": "General Register Office fee", "pence": 800}]
    assert "Ask the General Register Office before publishing" in order["rights_label"]
    url = f"/api/v1/record-orders/{order['id']}"
    early = alice_client.patch(url, {"status": "received"}, content_type=JSON)
    assert early.status_code == 409  # not ordered yet
    o = alice_client.patch(url, {"status": "ordered", "reference": "GRO-12345"}, content_type=JSON)
    assert o.json()["status"] == "ordered" and o.json()["ordered_at"]
    no_file = alice_client.patch(url, {"status": "received"}, content_type=JSON)
    assert no_file.status_code == 422
    up = alice_client.post(f"/api/v1/projects/{project.id}/files",
                           {"file": SimpleUploadedFile("birth.pdf", b"%PDF-1.4 test")})  # fmt: skip
    f = FileAsset.objects.get(pk=up.json()["id"])
    done = alice_client.patch(url, {"status": "received", "file_id": str(f.id)}, content_type=JSON)
    assert done.json()["status"] == "received" and done.json()["file_id"] == str(f.id)
    assert [x["id"] for x in alice_client.get("/api/v1/record-orders").json()] == [order["id"]]
    assert bob_client.get("/api/v1/record-orders").json() == []
    assert bob_client.patch(url, {"note": "x"}, content_type=JSON).status_code == 404
