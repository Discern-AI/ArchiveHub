"""WP10: previews, updating a tree from a new export, and undo."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from archive.models import FileAsset
from genealogy.models import ChangeSet, ExternalId, Relationship
from history.models import Assertion, Person
from projects.models import Project

pytestmark = pytest.mark.django_db
JSON = "application/json"

V1 = b"""0 HEAD
1 GEDC
2 VERS 5.5.1
1 NOTE SYNTHETIC TEST DATA.
0 @I1@ INDI
1 NAME Ada /Example/
1 BIRT
2 DATE 1850
1 DEAT
2 DATE 1920
1 FAMS @F1@
0 @I2@ INDI
1 NAME Ben /Example/
1 BIRT
2 DATE 1880
1 DEAT
2 DATE 1950
1 FAMC @F1@
0 @I3@ INDI
1 NAME Cy /Gone/
1 BIRT
2 DATE 1700
1 DEAT
2 DATE 1760
0 @F1@ FAM
1 WIFE @I1@
1 CHIL @I2@
0 TRLR
"""

# A later export of the same tree: Ada's birth corrected, Dot added, Cy removed, and @I3@
# reused for someone quite different.
V2 = b"""0 HEAD
1 GEDC
2 VERS 5.5.1
1 NOTE SYNTHETIC TEST DATA.
0 @I1@ INDI
1 NAME Ada /Example/
1 BIRT
2 DATE 1851
1 DEAT
2 DATE 1920
1 FAMS @F1@
0 @I2@ INDI
1 NAME Ben /Example/
1 BIRT
2 DATE 1880
1 DEAT
2 DATE 1950
1 FAMC @F1@
0 @I3@ INDI
1 NAME Zed /Stranger/
1 BIRT
2 DATE 1900
1 DEAT
2 DATE 1970
0 @I4@ INDI
1 NAME Dot /Example/
1 BIRT
2 DATE 1882
1 DEAT
2 DATE 1960
1 FAMC @F1@
0 @F1@ FAM
1 WIFE @I1@
1 CHIL @I2@
1 CHIL @I4@
0 TRLR
"""


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, title="Example family")


def upload(client, project, name, data):
    r = client.post(
        f"/api/v1/projects/{project.id}/files", {"file": SimpleUploadedFile(name, data)}
    )
    assert r.status_code == 201, r.content
    return FileAsset.objects.get(pk=r.json()["id"])


def run_import(client, f, **options):
    r = client.post(f"/api/v1/files/{f.id}/jobs", {"kind": "gedcom_import", "options": options},
                    content_type=JSON)  # fmt: skip
    job = r.json()
    assert job["status"] == "done", job
    return job["result"]


def birth(person):
    from genealogy.exporter import current_values

    return current_values(person.project, [person.id])[person.id]["birth date"].value


def test_import_can_be_undone_in_one_step(alice_client, project):
    f = upload(alice_client, project, "v1.ged", V1)
    result = run_import(alice_client, f)
    assert Person.objects.filter(project=project).count() == 3
    changes = alice_client.get(f"/api/v1/projects/{project.id}/changes").json()
    assert changes[0]["summary"] == "Imported v1.ged: 3 people" and changes[0]["blocked"] == []
    r = alice_client.post(f"/api/v1/projects/{project.id}/changes/{result['change_set']}/undo")
    assert r.status_code == 200, r.content
    assert not Person.objects.filter(project=project).exists()
    assert not Assertion.objects.filter(project=project).exists()
    assert not Relationship.objects.filter(project=project).exists()
    assert not ExternalId.objects.filter(project=project).exists()
    assert FileAsset.objects.filter(pk=f.id).exists()  # the file itself stays
    again = alice_client.post(f"/api/v1/projects/{project.id}/changes/{result['change_set']}/undo")
    assert again.status_code == 409


def test_preview_then_update_from_a_new_export(alice_client, project):
    first = run_import(alice_client, upload(alice_client, project, "v1.ged", V1))
    trees = alice_client.get(f"/api/v1/projects/{project.id}/trees").json()
    assert trees == [{"tree": first["tree"], "first_file": "v1.ged", "people": 3,
                      "last_updated": trees[0]["last_updated"], "last_file": "v1.ged"}]  # fmt: skip
    f2 = upload(alice_client, project, "v2.ged", V2)
    before = Person.objects.count(), Assertion.objects.count()
    preview = alice_client.get(f"/api/v1/files/{f2.id}/gedcom-preview",
                               {"mode": "update", "base": first["tree"]}).json()  # fmt: skip
    assert (preview["added"], preview["updated"]) == (2, 2)  # Dot and Zed new; Ada, Ben matched
    assert preview["not_in_file"] == ["Cy Gone"]  # kept, and said
    assert preview["id_but_not_name"] == [
        {"id": "@I3@", "in_tree": "Cy Gone", "in_file": "Zed Stranger"}
    ]
    assert isinstance(preview["health"]["findings"], list)
    assert (Person.objects.count(), Assertion.objects.count()) == before  # nothing saved
    assert not ChangeSet.objects.filter(kind="update").exists()

    result = run_import(alice_client, f2, mode="update", base=first["tree"])
    assert result["mode"] == "update" and (result["added"], result["updated"]) == (2, 2)
    ada = Person.objects.get(project=project, name="Ada Example")
    assert birth(ada) == "1851"  # the newer export wins over the older one
    assert Person.objects.filter(project=project).count() == 5  # Ada, Ben, Cy kept, Dot, Zed
    assert Person.objects.filter(project=project, name="Ada Example").count() == 1  # no copies
    dot = Person.objects.get(name="Dot Example")
    assert Relationship.objects.filter(person=ada, relative=dot, kind="parent").exists()

    # Undo the update: Ada's earlier birth year is current again, Dot and Zed are gone.
    alice_client.post(f"/api/v1/projects/{project.id}/changes/{result['change_set']}/undo")
    assert birth(Person.objects.get(name="Ada Example")) == "1850"
    assert not Person.objects.filter(name__in=["Dot Example", "Zed Stranger"]).exists()
    assert Person.objects.filter(project=project).count() == 3


def test_undo_waits_for_later_changes_and_your_own_facts(alice_client, project):
    first = run_import(alice_client, upload(alice_client, project, "v1.ged", V1))
    second = run_import(
        alice_client, upload(alice_client, project, "v2.ged", V2), mode="update", base=first["tree"]
    )
    url = f"/api/v1/projects/{project.id}/changes"
    r = alice_client.post(f"{url}/{first['change_set']}/undo")
    assert r.status_code == 409 and "Undo the later change first" in r.json()["detail"]
    alice_client.post(f"{url}/{second['change_set']}/undo")
    # A fact you added yourself to an imported person would be lost, so undo waits.
    ben = Person.objects.get(name="Ben Example")
    alice_client.post(f"/api/v1/projects/{project.id}/people/{ben.id}/claims",
                      {"predicate": "occupation", "value": "Carter", "status": "documented",
                       "note": ""}, content_type=JSON)  # fmt: skip
    r = alice_client.post(f"{url}/{first['change_set']}/undo")
    assert r.status_code == 409 and "1 fact added since" in r.json()["detail"]
    listed = {c["id"]: c for c in alice_client.get(url).json()}
    assert listed[first["change_set"]]["blocked"]


def test_update_needs_a_tree_from_this_project(alice_client, bob_client, project):
    f = upload(alice_client, project, "v1.ged", V1)
    r = alice_client.get(
        f"/api/v1/files/{f.id}/gedcom-preview", {"mode": "update", "base": "gedcom:nope"}
    )
    assert r.status_code == 422 and "wasn't found" in r.json()["detail"]
    assert bob_client.get(f"/api/v1/files/{f.id}/gedcom-preview").status_code == 404
    first = run_import(alice_client, f)
    assert (
        bob_client.post(
            f"/api/v1/projects/{project.id}/changes/{first['change_set']}/undo"
        ).status_code
        == 404
    )
