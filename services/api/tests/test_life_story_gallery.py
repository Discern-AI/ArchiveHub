"""WP11: Life Story pages, galleries and photo suggestions."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from archive.models import FileAsset
from genealogy.life_story import say_date
from genealogy.models import GalleryItem, GalleryTag
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
1 NAME Arthur /Sample/
1 SEX M
1 BIRT
2 DATE ABT 1890
2 PLAC Newbury, Berkshire
1 RESI
2 DATE 1911
2 PLAC Reading, Berkshire
1 OCCU Publican
1 DEAT
2 DATE 14 MAR 1960
2 PLAC Reading, Berkshire
1 FAMS @F1@
1 FAMC @F0@
0 @I2@ INDI
1 NAME Edith /Fictional/
1 SEX F
1 BIRT
2 DATE 1892
1 DEAT
2 DATE 1970
1 FAMS @F1@
0 @I3@ INDI
1 NAME Alice /Sample/
1 SEX F
1 BIRT
2 DATE 1915
1 DEAT
2 DATE 1999
1 FAMC @F1@
0 @I4@ INDI
1 NAME Young /Sample/
1 BIRT
2 DATE 1950
1 FAMC @F1@
0 @I5@ INDI
1 NAME Walter /Sample/
1 SEX M
1 BIRT
2 DATE 1860
1 DEAT
2 DATE 1930
1 FAMS @F0@
0 @F0@ FAM
1 HUSB @I5@
1 CHIL @I1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 MARR
2 DATE 4 JUN 1914
2 PLAC Newbury
1 CHIL @I3@
1 CHIL @I4@
0 TRLR
"""


def png() -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (40, 30), (120, 80, 40)).save(out, "PNG")
    return out.getvalue()


@pytest.fixture
def project(alice, alice_client):
    project = Project.objects.create(owner=alice, title="Samples")
    r = alice_client.post(
        f"/api/v1/projects/{project.id}/files", {"file": SimpleUploadedFile("t.ged", GED)}
    )
    f = FileAsset.objects.get(pk=r.json()["id"])
    job = alice_client.post(
        f"/api/v1/files/{f.id}/jobs", {"kind": "gedcom_import"}, content_type=JSON
    ).json()
    assert job["status"] == "done", job
    return project


def person(project, xref):
    return Person.objects.get(project=project, external_id=xref)


def upload_image(client, project, name, folder=None):
    data = {"file": SimpleUploadedFile(name, png(), content_type="image/png")}
    if folder:
        data["folder_id"] = str(folder.id)
    r = client.post(f"/api/v1/projects/{project.id}/files", data)
    assert r.status_code == 201, r.content
    return FileAsset.objects.get(pk=r.json()["id"])


def test_dates_read_as_words():
    assert say_date("ABT 1850") == "about 1850"
    assert say_date("14 MAR 1988") == "14 March 1988"
    assert say_date("BET 1990 AND 1992") == "between 1990 and 1992"
    assert say_date("BEF 1953") == "before 1953"
    assert say_date("summer 1952") == "summer 1952"  # kept as written


def test_life_story_in_order_with_sources_and_gaps(alice_client, project):
    load_overlays()
    arthur = person(project, "@I1@")
    s = alice_client.get(f"/api/v1/projects/{project.id}/people/{arthur.id}/life-story").json()
    assert not s["private"]
    sentences = [e["sentence"] for c in s["chapters"] for e in c["events"]]
    assert sentences == [
        "Arthur was born about 1890 in Newbury, Berkshire.",
        "Child of Walter Sample.",
        "Married Edith Fictional on 4 June 1914 at Newbury.",
        "Their daughter Alice Sample was born in 1915.",
        "Had a child who may still be living (details private).",
        "Recorded living in Reading, Berkshire in 1911.",
        "Worked as a publican.",  # undated events come after dated ones
        "Arthur died on 14 March 1960 in Reading, Berkshire, aged about 70.",
    ]
    assert [c["title"] for c in s["chapters"]] == [
        "Early life", "Marriage and family", "Work and homes", "Later life"
    ]  # fmt: skip
    born = s["chapters"][0]["events"][0]
    assert born["sources"][0]["title"].startswith("t.ged") and born["status"] == "documented"
    assert born["claim_ids"]
    assert "Young" not in str(s)  # a living child is never named
    assert s["at_a_glance"]["born"] == "about 1890, Newbury, Berkshire"
    assert s["gaps"] == []
    wars = {c["title"]: c for c in s["context"]}
    assert wars["First World War"]["age"] == "about 24 to 28"
    census = [c for c in s["context"] if c["title"] == "Census"]
    assert census[0]["date_text"] == "5 April 1891" and census[0]["age"] == "about 1"
    assert census[0]["note"] == "They could appear in it."
    assert "1931 census destroyed" not in wars  # not something they lived through
    assert "doesn't say they took part" in s["context_note"]
    # Living people's lives aren't told.
    young = person(project, "@I4@")
    priv = alice_client.get(f"/api/v1/projects/{project.id}/people/{young.id}/life-story").json()
    assert priv["private"] and "chapters" not in priv
    # Walter has no occupation or addresses: listed as gaps to look into.
    walter = person(project, "@I5@")
    w = alice_client.get(f"/api/v1/projects/{project.id}/people/{walter.id}/life-story").json()
    assert "No occupation recorded." in w["gaps"] and "No parents recorded." in w["gaps"]


def test_one_photo_in_several_galleries(alice_client, bob_client, project):
    arthur, edith = person(project, "@I1@"), person(project, "@I2@")
    wedding = upload_image(alice_client, project, "wedding.png")
    street = upload_image(alice_client, project, "cheap-street.png")
    base = f"/api/v1/projects/{project.id}"
    r = alice_client.post(f"{base}/gallery", {"file_id": str(wedding.id), "caption": "Their wedding",
                          "date_text": "June 1914", "tags": [{"person_id": str(arthur.id)},
                          {"person_id": str(edith.id)}]}, content_type=JSON)  # fmt: skip
    assert r.status_code == 201 and r.json()["year"] == 1914 and r.json()["decade"] == "1910s"
    alice_client.post(f"{base}/gallery", {"file_id": str(street.id), "tags": [
        {"person_id": str(arthur.id), "relation": "context"}]}, content_type=JSON)  # fmt: skip
    a = alice_client.get(f"{base}/people/{arthur.id}/gallery").json()
    assert [(i["file_name"], i["relation"]) for i in a] == [
        ("wedding.png", "shows"), ("cheap-street.png", "context")
    ]  # fmt: skip
    assert {p["name"] for p in a[0]["people"]} == {"Arthur Sample", "Edith Fictional"}
    assert [
        i["file_name"] for i in alice_client.get(f"{base}/people/{edith.id}/gallery").json()
    ] == ["wedding.png"]
    # Reorder, then untag and remove: the file stays in the Archive.
    ids = [i["id"] for i in a]
    alice_client.put(f"{base}/people/{arthur.id}/gallery/order", {"item_ids": ids[::-1]},
                     content_type=JSON)  # fmt: skip
    assert alice_client.get(f"{base}/people/{arthur.id}/gallery").json()[0]["file_name"] == (
        "cheap-street.png"
    )
    alice_client.delete(f"{base}/gallery/{ids[0]}/tags/{edith.id}")
    assert alice_client.get(f"{base}/people/{edith.id}/gallery").json() == []
    assert alice_client.delete(f"{base}/gallery/{ids[1]}").status_code == 204
    assert FileAsset.objects.filter(pk=street.id).exists()
    assert len(alice_client.get(f"{base}/gallery").json()) == 1
    # Only pictures and scans; nobody else can add or see.
    ged = FileAsset.objects.get(name="t.ged")
    r = alice_client.post(f"{base}/gallery", {"file_id": str(ged.id)}, content_type=JSON)
    assert r.status_code == 422
    assert bob_client.get(f"{base}/gallery").status_code == 404


def test_photo_suggestions_from_names_and_years(alice_client, project):
    from archive.models import Folder

    folder = Folder.objects.create(project=project, name="Sample family photos")
    upload_image(alice_client, project, "Arthur Sample 1945.png", folder)
    upload_image(alice_client, project, "Walter 1850.png", folder)  # before Walter was born
    upload_image(alice_client, project, "IMG_0001.png", folder)
    rows = {r["file_name"]: r for r in alice_client.get(
        f"/api/v1/projects/{project.id}/photo-suggestions", {"folder_id": folder.id}).json()}  # fmt: skip
    arthur = rows["Arthur Sample 1945.png"]
    assert arthur["year_hint"] == 1945 and arthur["year_from"] == "the file name"
    top = arthur["suggestions"][0]
    assert top["name"] == "Arthur Sample" and "the name says Arthur Sample" in top["reason"]
    assert "they were alive in 1945" in top["reason"]
    assert all(s["name"] != "Walter Sample" for s in rows["Walter 1850.png"]["suggestions"])
    assert rows["IMG_0001.png"]["suggestions"] == []
    # Once a picture is in a gallery it's no longer suggested.
    f = FileAsset.objects.get(name="IMG_0001.png")
    GalleryItem.objects.create(project=project, file=f)
    names = [r["file_name"] for r in alice_client.get(
        f"/api/v1/projects/{project.id}/photo-suggestions").json()]  # fmt: skip
    assert "IMG_0001.png" not in names


def test_merge_and_removal_carry_gallery_tags(alice_client, project):
    arthur, alice_s = person(project, "@I1@"), person(project, "@I3@")
    photo = upload_image(alice_client, project, "p.png")
    item = GalleryItem.objects.create(project=project, file=photo)
    GalleryTag.objects.create(item=item, person=alice_s)
    r = alice_client.post(f"/api/v1/projects/{project.id}/people/{alice_s.id}/delete", {},
                          content_type=JSON)  # fmt: skip
    assert not GalleryTag.objects.filter(item=item).exists()
    alice_client.post(f"/api/v1/projects/{project.id}/changes/{r.json()['change_set']}/undo")
    assert GalleryTag.objects.filter(item=item, person_id=alice_s.id).exists()
    assert arthur  # untouched
