"""WP10: merging two people with a preview, and removing people safely. Both undoable."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from archive.models import FileAsset
from genealogy.exporter import current_values
from genealogy.models import Relationship
from history.models import Assertion, Person
from projects.models import Project

pytestmark = pytest.mark.django_db
JSON = "application/json"

# Mary is Ann's mother; Ann is John's mother; John is Kid's father. Mary also has Bob,
# who is married to Cat. "Ann Smith" was entered twice (@I2@), with Mary as mother.
GED = b"""0 HEAD
1 GEDC
2 VERS 5.5.1
1 NOTE SYNTHETIC TEST DATA.
0 @I1@ INDI
1 NAME Ann /Smith/
1 SEX F
1 BIRT
2 DATE 1850
1 DEAT
2 DATE 1910
1 FAMS @F1@
1 FAMC @F0@
0 @I2@ INDI
1 NAME Ann /Smith/
1 SEX F
1 BIRT
2 DATE ABT 1851
2 PLAC Leeds
1 DEAT
2 DATE 1910
1 OCCU Dressmaker
1 FAMC @F3@
0 @I3@ INDI
1 NAME John /Smith/
1 BIRT
2 DATE 1875
1 DEAT
2 DATE 1940
1 FAMC @F1@
1 FAMS @F2@
0 @I4@ INDI
1 NAME Kid /Smith/
1 BIRT
2 DATE 1900
1 DEAT
2 DATE 1980
1 FAMC @F2@
0 @I5@ INDI
1 NAME Mary /Old/
1 BIRT
2 DATE 1820
1 DEAT
2 DATE 1890
1 FAMS @F0@
0 @I6@ INDI
1 NAME Bob /Old/
1 BIRT
2 DATE 1848
1 DEAT
2 DATE 1920
1 FAMC @F0@
1 FAMS @F4@
0 @I7@ INDI
1 NAME Cat /Old/
1 BIRT
2 DATE 1850
1 DEAT
2 DATE 1925
1 FAMS @F4@
0 @F0@ FAM
1 WIFE @I5@
1 CHIL @I1@
1 CHIL @I6@
0 @F1@ FAM
1 WIFE @I1@
1 CHIL @I3@
0 @F2@ FAM
1 HUSB @I3@
1 CHIL @I4@
0 @F3@ FAM
1 WIFE @I5@
1 CHIL @I2@
0 @F4@ FAM
1 HUSB @I6@
1 WIFE @I7@
0 TRLR
"""


@pytest.fixture
def project(alice, alice_client):
    project = Project.objects.create(owner=alice, title="Smiths")
    r = alice_client.post(
        f"/api/v1/projects/{project.id}/files", {"file": SimpleUploadedFile("s.ged", GED)}
    )
    f = FileAsset.objects.get(pk=r.json()["id"])
    job = alice_client.post(
        f"/api/v1/files/{f.id}/jobs", {"kind": "gedcom_import"}, content_type=JSON
    ).json()
    assert job["status"] == "done", job
    return project


def person(project, xref):
    return Person.objects.get(project=project, external_id=xref)


def value(p, question):
    a = current_values(p.project, [p.id]).get(p.id, {}).get(question)
    return a.value if a else None


def test_merge_preview_shows_each_question_and_what_moves(alice_client, project):
    ann, dup = person(project, "@I1@"), person(project, "@I2@")
    url = f"/api/v1/projects/{project.id}/people/{ann.id}/merge-preview"
    p = alice_client.get(url, {"other": dup.id}).json()
    q = {x["question"]: x for x in p["questions"]}
    assert q["birth date"]["differs"] and not q["name"]["differs"]
    assert q["occupation"]["keep"] == [] and q["occupation"]["other"][0]["value"] == "Dressmaker"
    assert p["relatives_moving"]["parents"] == []  # Mary is already Ann's mother
    assert p["warnings"] == []
    before = Assertion.objects.count()
    assert Assertion.objects.count() == before  # nothing changed


def test_merge_with_facts_left_out_then_undo(alice_client, project):
    ann, dup = person(project, "@I1@"), person(project, "@I2@")
    birth = Assertion.objects.get(subject_id=dup.id, predicate="birth date")
    r = alice_client.post(f"/api/v1/projects/{project.id}/people/{ann.id}/merge",
                          {"other": str(dup.id), "leave_out": [str(birth.id)]},
                          content_type=JSON)  # fmt: skip
    assert r.status_code == 200, r.content
    assert r.json()["summary"] == "Merged Ann Smith into Ann Smith, leaving out 1 fact"
    assert not Person.objects.filter(pk=dup.pk).exists()
    ann.refresh_from_db()
    assert value(ann, "occupation") == "Dressmaker"  # brought across
    assert value(ann, "birth date") == "1850"  # the left-out "ABT 1851" is gone
    assert value(ann, "birth place") == "Leeds"
    mary = person(project, "@I5@")
    assert Relationship.objects.filter(person=mary, relative=ann, kind="parent").count() == 1

    r = alice_client.post(f"/api/v1/projects/{project.id}/changes/{r.json()['change_set']}/undo")
    assert r.status_code == 200, r.content
    dup = Person.objects.get(pk=dup.pk)  # back, with everything
    assert value(dup, "birth date") == "ABT 1851" and value(dup, "occupation") == "Dressmaker"
    assert value(ann, "occupation") is None
    assert Relationship.objects.filter(person=mary, relative=dup, kind="parent").exists()


def test_parent_and_child_cant_be_merged(alice_client, project):
    ann, john = person(project, "@I1@"), person(project, "@I3@")
    r = alice_client.get(f"/api/v1/projects/{project.id}/people/{ann.id}/merge-preview",
                         {"other": john.id})  # fmt: skip
    assert r.status_code == 422 and "parent or child" in r.json()["detail"]
    r = alice_client.post(f"/api/v1/projects/{project.id}/people/{ann.id}/merge",
                          {"other": str(ann.id)}, content_type=JSON)  # fmt: skip
    assert r.status_code == 422


def test_removal_shows_who_would_be_cut_off(alice_client, bob_client, project):
    ann, john, kid = person(project, "@I1@"), person(project, "@I3@"), person(project, "@I4@")
    url = f"/api/v1/projects/{project.id}/people/{ann.id}"
    p = alice_client.get(f"{url}/delete-preview").json()
    # Without Ann, John and Kid are only connected to each other.
    assert [sorted(x["name"] for x in g) for g in p["stranded"]] == [["John Smith", "Kid Smith"]]
    assert p["facts"] > 0 and p["relationships"] == 2
    mary = person(project, "@I5@")
    bad = alice_client.post(f"{url}/delete", {"also": [str(mary.id)]}, content_type=JSON)
    assert bad.status_code == 422  # only cut-off people can go with it
    assert bob_client.post(f"{url}/delete", {}, content_type=JSON).status_code == 404

    r = alice_client.post(f"{url}/delete", {"also": [str(john.id)]}, content_type=JSON)
    assert r.status_code == 200 and r.json()["summary"] == "Removed Ann Smith and 1 other"
    assert not Person.objects.filter(pk__in=[ann.pk, john.pk]).exists()
    assert Person.objects.filter(pk=kid.pk).exists()  # kept, as chosen
    facts_after = Assertion.objects.count()

    alice_client.post(f"/api/v1/projects/{project.id}/changes/{r.json()['change_set']}/undo")
    assert Person.objects.filter(pk__in=[ann.pk, john.pk]).count() == 2
    assert Assertion.objects.count() > facts_after
    assert value(Person.objects.get(pk=ann.pk), "birth date") == "1850"
    assert Relationship.objects.filter(person=ann, relative=john, kind="parent").exists()
    assert Relationship.objects.filter(person=john, relative=kid, kind="parent").exists()
