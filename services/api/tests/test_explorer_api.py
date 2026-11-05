import pytest
from django.test import Client

from core.models import AuditLog
from explorer.models import BasketItem
from history.loader import load_all
from history.models import Assertion, Decision, Organisation
from projects.models import Project, ProjectMember, Role

pytestmark = pytest.mark.django_db
JSON = "application/json"


@pytest.fixture
def ref(db):
    load_all()


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, title="The Pigeons")


def test_sources_list_says_what_is_available(ref, alice_client):
    sources = {s["key"]: s for s in alice_client.get("/api/v1/explorer/sources").json()}
    assert sources["checked-reference"]["available"] is True
    assert sources["old-map-names"]["available"] is False  # not imported in this test
    assert sources["wikidata"]["access_type"] == "live_api"


def test_search_and_record(ref, alice_client):
    r = alice_client.get("/api/v1/explorer/checked-reference/search?q=Pigeons&page_size=2")
    data = r.json()
    assert len(data["records"]) == 2 and data["next_cursor"]
    rid = data["records"][0]["id"]
    detail = alice_client.get(f"/api/v1/explorer/checked-reference/records/{rid}").json()
    assert detail["citation"] and detail["storage"] == "reference_only"
    assert alice_client.get("/api/v1/explorer/nope/search").status_code == 404
    assert alice_client.get("/api/v1/explorer/checked-reference/records/zzz").status_code == 404


def test_explorer_needs_login(ref):
    assert Client().get("/api/v1/explorer/sources").status_code == 401


def test_basket_keeps_reference_only_without_a_copy(ref, alice_client, project):
    url = f"/api/v1/projects/{project.id}/basket"
    body = {"connector": "checked-reference", "record_id": "closedpubs-pigeons"}
    r = alice_client.post(url, body, content_type=JSON)
    assert r.status_code == 201
    item = BasketItem.objects.get()
    assert item.storage == "reference_only" and item.snapshot is None
    assert item.url.startswith("https://www.closedpubs.co.uk/")
    assert alice_client.post(url, body, content_type=JSON).status_code == 200  # no duplicate
    assert BasketItem.objects.count() == 1
    assert [i["title"] for i in alice_client.get(url).json()] == [item.title]
    assert alice_client.delete(f"{url}/{item.id}").status_code == 204
    assert {"basket.add", "basket.remove"} <= set(AuditLog.objects.values_list("action", flat=True))


def test_basket_permissions(ref, project, bob, bob_client):
    url = f"/api/v1/projects/{project.id}/basket"
    body = {"connector": "checked-reference", "record_id": "closedpubs-pigeons"}
    assert bob_client.get(url).status_code == 404
    assert bob_client.post(url, body, content_type=JSON).status_code == 404
    ProjectMember.objects.create(project=project, user=bob, role=Role.VIEWER)
    assert bob_client.get(url).status_code == 200
    assert bob_client.post(url, body, content_type=JSON).status_code == 404


def test_evidence_and_decisions(ref, alice_client, project):
    pigeons = Organisation.objects.get(key="pigeons")
    url = f"/api/v1/evidence/organisation/{pigeons.id}?predicate=address&project_id={project.id}"
    data = alice_client.get(url).json()
    assert data["disputed"] is True and data["decision"] is None
    values = {c["value"]: c for c in data["claims"]}
    assert values["69 Cheap Street"]["evidence"][0]["suggested_weight"] == "weaker"
    assert values["5 Cheap Street"]["evidence"][0]["weight_suggested_by"] == "editor"

    put = f"/api/v1/projects/{project.id}/decisions"
    base = {"subject_type": "organisation", "subject_id": str(pigeons.id), "predicate": "address"}
    # Must choose exactly one: an answer, or keep it disputed.
    assert alice_client.put(put, base, content_type=JSON).status_code == 422
    chosen = values["5 Cheap Street"]["id"]
    r = alice_client.put(put, {**base, "chosen_id": chosen, "reason": "Three sources agree"},
                         content_type=JSON)  # fmt: skip
    assert r.status_code == 200
    assert alice_client.get(url).json()["decision"]["chosen_id"] == chosen
    # Changing the decision updates it; nothing is deleted.
    r = alice_client.put(put, {**base, "keep_disputed": True}, content_type=JSON)
    assert r.status_code == 200 and Decision.objects.count() == 1
    assert Assertion.objects.filter(subject_id=pigeons.id, predicate="address").count() == 3


def test_decision_rejects_claims_about_another_question(ref, alice_client, project):
    pigeons = Organisation.objects.get(key="pigeons")
    licensee = Assertion.objects.filter(subject_id=pigeons.id, predicate="licensee").first()
    r = alice_client.put(
        f"/api/v1/projects/{project.id}/decisions",
        {"subject_type": "organisation", "subject_id": str(pigeons.id), "predicate": "address",
         "chosen_id": str(licensee.id)},
        content_type=JSON,
    )  # fmt: skip
    assert r.status_code == 404


def test_only_editors_decide(ref, project, bob, bob_client):
    pigeons = Organisation.objects.get(key="pigeons")
    ProjectMember.objects.create(project=project, user=bob, role=Role.VIEWER)
    r = bob_client.put(
        f"/api/v1/projects/{project.id}/decisions",
        {"subject_type": "organisation", "subject_id": str(pigeons.id), "predicate": "address",
         "keep_disputed": True},
        content_type=JSON,
    )  # fmt: skip
    assert r.status_code == 404
