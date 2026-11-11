"""WP14: culture links and the Life Report."""

from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from archive.models import FileAsset
from culture.models import CultureItem, LifeReport
from culture.report import load_items
from genealogy.overlays import load_overlays
from history.models import Person
from projects.models import Project

pytestmark = pytest.mark.django_db
JSON = "application/json"

GED = b"""0 HEAD
1 GEDC
2 VERS 5.5.1
1 NOTE SYNTHETIC TEST DATA.
0 @I1@ INDI
1 NAME Thomas /Example/
1 SEX M
1 BIRT
2 DATE 1825
2 PLAC Hungerford, Berkshire, England
1 OCCU Agricultural labourer
1 RESI
2 DATE 1851
2 PLAC Kintbury, Berkshire, England
1 DEAT
2 DATE 1890
2 PLAC Newbury, Berkshire, England
0 @I2@ INDI
1 NAME Sarah /Example/
1 SEX F
1 BIRT
2 DATE 1860
1 DEAT
2 DATE 1930
1 OCCU Publican
0 @I3@ INDI
1 NAME Living /Example/
1 BIRT
2 DATE 1990
1 OCCU Agricultural labourer
0 TRLR
"""


@pytest.fixture
def project(alice, alice_client):
    load_items()
    load_overlays()
    project = Project.objects.create(owner=alice, title="Examples")
    r = alice_client.post(
        f"/api/v1/projects/{project.id}/files", {"file": SimpleUploadedFile("t.ged", GED)}
    )
    f = FileAsset.objects.get(pk=r.json()["id"])
    job = alice_client.post(
        f"/api/v1/files/{f.id}/jobs", {"kind": "gedcom_import"}, content_type=JSON
    ).json()
    assert job["status"] == "done", job
    return project


def report(client, project, xref, length="long"):
    p = Person.objects.get(project=project, external_id=xref)
    url = f"/api/v1/projects/{project.id}/people/{p.id}/life-report"
    return p, client.get(url, {"length": length}).json()


def test_a_berkshire_labourers_report_has_three_licensed_culture_items(alice_client, project):
    _, r = report(alice_client, project, "@I1@")
    assert not r["private"] and r["cost"].startswith("Free")
    culture = [b for b in r["blocks"] if b["type"] == "culture"]
    assert len(culture) >= 3
    for b in culture:
        item = CultureItem.objects.get(key=b["key"])
        assert item.status == "approved" and item.rights == "open"
        assert b["why"] and "kind of work recorded for Thomas (Agricultural labourer)" in b["why"]
        assert b["label"].startswith("This shows their world, not them.")
        assert b["credit"] and b["licence"] and b["source_url"]
        assert b["image_url"] or b["text"]  # shown because the rights are open
    # English items first, with the reason given.
    assert "It's English, like the places in their records." in culture[0]["why"]
    assert any(b["text"] for b in culture) and any(b["image_url"] for b in culture)
    headings = [b["text"] for b in r["blocks"] if b["type"] == "heading"]
    assert headings[-2:] == ["How artists and writers saw their world", "Sources and gaps"]
    assert "The world around them" in headings
    assert r["blocks"][0] == {"type": "title", "text": "Thomas Example"}


def test_rights_and_approval_decide_what_is_shown(alice_client, project):
    CultureItem.objects.filter(key="met-rowlandson-haymakers").update(rights="link_only")
    CultureItem.objects.exclude(key="met-rowlandson-haymakers").filter(kind="rhyme").update(
        status="proposed"
    )
    _, r = report(alice_client, project, "@I1@")
    culture = {b["key"]: b for b in r["blocks"] if b["type"] == "culture"}
    assert not any(k.startswith("halliwell") for k in culture)  # not approved: never used
    if "met-rowlandson-haymakers" in culture:
        linked = culture["met-rowlandson-haymakers"]
        assert linked["image_url"] == "" and linked["link_only"] and linked["source_url"]


def test_a_publican_gets_the_innkeeper_rhyme_and_living_people_get_nothing(alice_client, project):
    _, r = report(alice_client, project, "@I2@")
    keys = [b["key"] for b in r["blocks"] if b["type"] == "culture"]
    assert keys == ["halliwell-innkeeper"]
    _, living = report(alice_client, project, "@I3@")
    assert living["private"] and "blocks" not in living


def test_saving_keeps_edits_but_not_tampered_images(alice_client, bob_client, project):
    thomas, r = report(alice_client, project, "@I1@", "short")
    blocks = r["blocks"]
    para = next(b for b in blocks if b["type"] == "paragraph")
    para["text"] = "Edited by the family."
    art = next(b for b in blocks if b["type"] == "culture" and b["image_url"])
    art["image_url"] = "https://example.com/not-licensed.jpg"
    art["why"] = "Chosen because Thomas worked the fields."
    url = f"/api/v1/projects/{project.id}/people/{thomas.id}/life-reports"
    saved = alice_client.post(url, {"length": "short", "blocks": blocks}, content_type=JSON)
    assert saved.status_code == 201
    stored = LifeReport.objects.get()
    assert any(b.get("text") == "Edited by the family." for b in stored.blocks)
    kept = next(b for b in stored.blocks if b.get("key") == art["key"])
    assert kept["image_url"] == CultureItem.objects.get(key=art["key"]).image_url  # not tampered
    assert kept["why"] == "Chosen because Thomas worked the fields."
    bad = alice_client.post(url, {"blocks": [{"type": "culture", "key": "nope"}]},
                            content_type=JSON)  # fmt: skip
    assert bad.status_code == 422
    odd = alice_client.post(url, {"blocks": [{"type": "script", "text": "x"}]}, content_type=JSON)
    assert odd.status_code == 422
    assert bob_client.post(url, {"blocks": []}, content_type=JSON).status_code == 404
    assert len(alice_client.get(url).json()) == 1


def test_starter_items_record_their_rights_check():
    load_items()
    for item in CultureItem.objects.all():
        assert item.rights_checked_on == date(2026, 11, 11)
        assert item.source_url.startswith("https://")
