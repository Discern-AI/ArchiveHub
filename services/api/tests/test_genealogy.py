import json
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from archive.models import FileAsset
from assistant.tools import ToolKit
from genealogy.gedcom import parse, parse_date
from genealogy.models import Relationship
from history.models import Assertion, Person
from projects.models import Project

pytestmark = pytest.mark.django_db
GED = (Path(__file__).parents[3] / "fixtures" / "illustrative" / "sample_family.ged").read_bytes()
JSON = "application/json"


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, title="Sample family")


@pytest.fixture
def imported(alice_client, project):
    r = alice_client.post(
        f"/api/v1/projects/{project.id}/files",
        {"file": SimpleUploadedFile("sample_family.ged", GED)},
    )
    assert r.status_code == 201, r.content
    f = FileAsset.objects.get()
    assert f.status == "needs_processing"
    job = alice_client.post(
        f"/api/v1/files/{f.id}/jobs", {"kind": "gedcom_import"}, content_type=JSON
    ).json()
    assert job["status"] == "done", job
    return f, job


def test_dates_keep_original_wording():
    assert vars(parse_date("ABT 1921")) == {
        "text": "ABT 1921",
        "year_from": 1921,
        "year_to": 1921,
        "precision": "approximate",
    }
    assert parse_date("BET 1990 AND 1992").precision == "range"
    assert parse_date("BEF 1953").year_to == 1953 and parse_date("BEF 1953").year_from is None
    assert parse_date("14 MAR 1988").precision == "exact"
    assert parse_date("unknown").precision == "unknown"


def test_parser_joins_continuations():
    (head, person) = parse("0 HEAD\n0 @I1@ INDI\n1 NOTE A keen\n2 CONC  cyclist.\n")
    assert person.first("NOTE").value == "A keen cyclist."


def test_import_creates_people_relationships_and_claims(imported, project):
    f, job = imported
    report = job["result"].pop("report")
    assert job["result"] == {"people": 5, "families": 2, "living_private": 2}
    assert report["gedcom_version"] == "5.5.1" and report["made_by"] == "ArchiveHubTestData"
    assert report["notes_not_imported"] == 1  # Tom's "keen cyclist" note
    assert report["source_citations_not_imported"] == 0 and report["media_references"] == 0
    arthur = Person.objects.get(project=project, external_id="@I1@")
    assert arthur.name == "Arthur Sample" and arthur.living_status == "deceased"
    # No death recorded and born within 110 years: treated as living, so private.
    alice_s = Person.objects.get(project=project, external_id="@I3@")
    assert alice_s.living_status == "living"
    walter = Person.objects.get(project=project, external_id="@I5@")
    assert walter.living_status == "deceased"  # born 1890: presumed dead
    birth = Assertion.objects.get(subject_id=arthur.id, predicate="birth date")
    assert (birth.date_text, birth.date_precision, birth.method) == (
        "ABT 1921",
        "approximate",
        "import",
    )
    ev = birth.evidence.get()
    assert ev.file_id == f.id and ev.location == "GEDCOM @I1@" and ev.record is None
    assert Relationship.objects.filter(project=project, kind="parent").count() == 5
    assert Relationship.objects.filter(project=project, kind="spouse").count() == 1


def test_reimport_does_not_duplicate(imported, alice_client, project):
    f, _ = imported
    before = (Person.objects.count(), Assertion.objects.count(), Relationship.objects.count())
    alice_client.post(f"/api/v1/files/{f.id}/jobs", {"kind": "gedcom_import"}, content_type=JSON)
    assert (
        Person.objects.count(),
        Assertion.objects.count(),
        Relationship.objects.count(),
    ) == before


def test_person_page_correction_and_export(imported, alice_client, project):
    arthur = Person.objects.get(project=project, external_id="@I1@")
    base = f"/api/v1/projects/{project.id}/people"
    detail = alice_client.get(f"{base}/{arthur.id}").json()
    assert [p["name"] for p in detail["parents"]] == ["Walter Sample"]
    assert sorted(p["name"] for p in detail["children"]) == ["Alice Sample", "Tom Sample"]
    assert [p["name"] for p in detail["partners"]] == ["Edith Fictional"]

    # Correct the birth date from memory: the imported claim stays beside it.
    r = alice_client.post(f"{base}/{arthur.id}/claims",
                          {"predicate": "birth date", "value": "1922", "status": "remembered",
                           "note": "Mum always said 1922"}, content_type=JSON)  # fmt: skip
    assert r.status_code == 201
    facts = {f["question"]: f for f in alice_client.get(f"{base}/{arthur.id}").json()["facts"]}
    birth = facts["birth date"]
    assert birth["disputed"] is True
    assert {(a["value"], a["method"], a["in_use"]) for a in birth["answers"]} == {
        ("ABT 1921", "import", False),
        ("1922", "user", True),
    }

    export = alice_client.get(f"/api/v1/projects/{project.id}/gedcom")
    text = export.content.decode()
    assert export["Content-Disposition"].startswith("attachment")
    assert "1 NAME Arthur /Sample/" in text and "2 DATE 1922" in text
    assert "Living person: keep private." in text
    assert text.startswith("0 HEAD") and text.rstrip().endswith("0 TRLR")
    # The export reads back in.
    people = [r for r in parse(text) if r.tag == "INDI"]
    assert len(people) == 5


def test_family_is_private(imported, project, bob_client, bob):
    arthur = Person.objects.get(project=project, external_id="@I1@")
    assert bob_client.get(f"/api/v1/projects/{project.id}/people").status_code == 404
    assert bob_client.get(f"/api/v1/projects/{project.id}/gedcom").status_code == 404
    assert bob_client.get(f"/api/v1/evidence/person/{arthur.id}?predicate=name").status_code == 404
    # The assistant can't find another user's relatives either.
    result = json.loads(ToolKit(user=bob).run("compare_claims", {"subject": "Arthur Sample"})[0])
    assert result["found"] is False


def test_assistant_finds_own_deceased_relatives_but_not_living_ones(imported, alice):
    kit = ToolKit(user=alice)
    found = json.loads(kit.run("compare_claims", {"subject": "Arthur Sample"})[0])
    assert found["found"] and found["subject"] == "Arthur Sample"
    living = json.loads(kit.run("compare_claims", {"subject": "Alice Sample"})[0])
    assert living.get("subject") != "Alice Sample"


def test_viewers_cannot_correct(imported, project, bob, bob_client):
    from projects.models import ProjectMember, Role

    ProjectMember.objects.create(project=project, user=bob, role=Role.VIEWER)
    arthur = Person.objects.get(project=project, external_id="@I1@")
    assert bob_client.get(f"/api/v1/projects/{project.id}/people/{arthur.id}").status_code == 200
    r = bob_client.post(f"/api/v1/projects/{project.id}/people/{arthur.id}/claims",
                        {"predicate": "name", "value": "X"}, content_type=JSON)  # fmt: skip
    assert r.status_code == 404


def test_gedcom_7_export(imported, alice_client, project):
    from genealogy.exporter import GEDCOM7_DATE, export_gedcom
    from genealogy.gedcom import parse

    r = alice_client.get(f"/api/v1/projects/{project.id}/gedcom", {"version": "7.0"})
    assert r.status_code == 200
    text = r.content.decode()
    head = text.split("0 @", 1)[0]
    assert "2 VERS 7.0" in head and "CHAR" not in head and "FORM" not in head
    assert "CONC" not in text  # GEDCOM 7 removed CONC
    assert "2 DATE ABT 1921" in text and "2 DATE BET 1990 AND 1992" in text
    records = parse(text)
    assert len([r for r in records if r.tag == "INDI"]) == 5
    assert (
        alice_client.get(f"/api/v1/projects/{project.id}/gedcom", {"version": "6"}).status_code
        == 422
    )
    # 5.5.1 stays the default.
    assert (
        "2 VERS 5.5.1" in alice_client.get(f"/api/v1/projects/{project.id}/gedcom").content.decode()
    )

    # Wording GEDCOM 7 can't parse is kept as a phrase.
    alice_client.post(
        f"/api/v1/projects/{project.id}/people/{Person.objects.get(name='Tom Sample').id}/claims",
        {"predicate": "birth date", "value": "summer 1952", "status": "remembered", "note": ""},
        content_type=JSON,
    )
    text = export_gedcom(project, "7.0")
    assert "2 DATE\n3 PHRASE summer 1952" in text
    for good in (
        "1921",
        "14 MAR 1988",
        "ABT 1921",
        "BET 1990 AND 1992",
        "FROM 1914 TO 1918",
        "BEF FEB 1953",
    ):
        assert GEDCOM7_DATE.fullmatch(good), good
    for bad in ("summer 1952", "c.1900", "1990-1992"):
        assert not GEDCOM7_DATE.fullmatch(bad), bad
