import json

import pytest
from django.contrib.contenttypes.models import ContentType

from assistant.tools import ToolKit
from history import queries
from history.loader import load_all
from history.models import Assertion, Organisation, Person, SourceRecord
from projects.models import Project

pytestmark = pytest.mark.django_db


@pytest.fixture
def reference(db):
    return load_all()


def test_loader_is_idempotent(reference):
    again = load_all()
    assert again == reference
    assert reference["sources"] >= 30
    assert SourceRecord.objects.count() == reference["records"]
    # Every stored third-party record was checked and links to its page (ADR-018).
    for r in SourceRecord.objects.all():
        assert r.checked_on and r.url.startswith("https://")
        assert r.storage == "reference_only"


def test_pigeons_address_is_disputed(reference, alice):
    pigeons = Organisation.objects.get(key="pigeons")
    claims = queries.claims_about(alice, pigeons)
    assert queries.is_disputed(claims["address"])
    assert {c.value for c in claims["address"]} == {
        "5 Cheap Street",
        "69 Cheap Street",
        "9 St Marys Hill",
    }
    # Many licensees is normal, not a dispute.
    assert not queries.is_disputed(claims["licensee"])
    # Nothing is recorded about closure: it stays unknown.
    assert "closed" not in claims


def test_project_claims_are_private_to_the_project(reference, alice, bob):
    pigeons = Organisation.objects.get(key="pigeons")
    project = Project.objects.create(owner=alice, title="Private research")
    Assertion.objects.create(
        subject_type=ContentType.objects.get_for_model(Organisation),
        subject_id=pigeons.id,
        predicate="closed",
        value="Alice's own note",
        project=project,
        method="user",
    )
    assert "closed" in queries.claims_about(alice, pigeons)
    assert "closed" not in queries.claims_about(bob, pigeons)
    bob_view = json.loads(ToolKit(user=bob).run("compare_claims", {"subject": "Pigeons"})[0])
    assert "closed" not in [q["question"] for q in bob_view["questions"]]


def test_living_people_are_not_surfaced(reference):
    Person.objects.create(name="Zebedee Quartermain", living_status="living")
    Person.objects.create(name="Zebedee Quartermain senior", living_status="deceased")
    found = [s.name for s in queries.find_subjects("Zebedee Quartermain")]
    assert found == ["Zebedee Quartermain senior"]


def test_directory_search_ranks_relevant_sources(reference):
    names = [s.name for s in queries.search_sources("pub licensing Berkshire")]
    assert names[0] == "Berkshire Record Office"
    assert "A Street Near You" not in names
