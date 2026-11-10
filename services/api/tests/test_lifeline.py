import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from archive.models import FileAsset
from conftest import make_user
from genealogy.lifeline import window
from genealogy.models import OverlayEvent, Residence
from genealogy.overlays import load_overlays
from projects.models import Project
from timemap.models import LocationStatus, PlaceLocation

pytestmark = pytest.mark.django_db
JSON = "application/json"

GED = b"""0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
1 NOTE SYNTHETIC TEST DATA.
0 @I1@ INDI
1 NAME Ada /Example/
1 SEX F
1 BIRT
2 DATE ABT 1850
2 PLAC Hungerford, Berkshire
1 RESI
2 DATE 1871
2 PLAC Reading, Berkshire
1 RESI
2 DATE 1881
2 PLAC London
1 BURI
2 DATE 1920
2 PLAC London
1 FAMS @F1@
0 @I2@ INDI
1 NAME Ben /Example/
1 SEX M
1 BIRT
2 DATE 1880
1 FAMC @F1@
0 @I3@ INDI
1 NAME Cara /Example/
1 SEX F
1 BIRT
2 DATE 1990
1 FAMC @F1@
0 @F1@ FAM
1 WIFE @I1@
1 CHIL @I2@
1 CHIL @I3@
0 TRLR
"""


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, title="Example family")


@pytest.fixture
def imported(alice_client, project):
    r = alice_client.post(
        f"/api/v1/projects/{project.id}/files", {"file": SimpleUploadedFile("t.ged", GED)}
    )
    assert r.status_code == 201, r.content
    f = FileAsset.objects.get()
    job = alice_client.post(
        f"/api/v1/files/{f.id}/jobs", {"kind": "gedcom_import"}, content_type=JSON
    ).json()
    assert job["status"] == "done", job
    return f


def test_date_windows_keep_their_uncertainty():
    assert window(1850, 1850, "approximate", "ABT 1850", "birth") == {
        "earliest": 1845, "latest": 1855, "certainty": "about", "text": "ABT 1850", "from": "birth"
    }  # fmt: skip
    assert window(None, 1953, "before", "BEF 1953", "birth")["earliest"] is None
    assert window(1990, 1992, "range", "BET 1990 AND 1992", "death")["latest"] == 1992
    # Death is on or just before burial; birth can be years before baptism.
    buried = window(1920, 1920, "year", "1920", "burial")
    assert (buried["earliest"], buried["latest"], buried["certainty"]) == (1919, 1920, "buried")
    baptised = window(1851, 1851, "year", "1851", "baptism")
    assert (baptised["earliest"], baptised["latest"]) == (1846, 1851)
    assert window(None, None, "unknown", "", "birth") is None


def test_residences_are_imported_in_order(imported):
    ada = list(
        Residence.objects.filter(person__name="Ada Example").values_list("place_text", "year_from")
    )
    assert ada == [("Reading, Berkshire", 1871), ("London", 1881)]


def test_lifeline_rows_places_and_privacy(imported, alice_client, project):
    load_overlays()
    PlaceLocation.objects.create(
        project=project, text="London", text_key="london", latitude=51.5, longitude=-0.12,
        status=LocationStatus.SUGGESTED,
    )  # fmt: skip
    data = alice_client.get(f"/api/v1/projects/{project.id}/lifeline").json()
    rows = {r["name"]: r for r in data["people"]}
    ada = rows["Ada Example"]
    assert ada["start"]["certainty"] == "about" and ada["start"]["earliest"] == 1845
    assert ada["end"]["certainty"] == "buried" and ada["end"]["latest"] == 1920
    assert [p["kind"] for p in ada["places"]] == ["birth", "residence", "residence", "burial"]
    london = ada["places"][2]
    assert london["latitude"] == 51.5 and london["located"] == "suggested"
    assert ada["places"][1]["latitude"] is None and ada["places"][1]["located"] == "not yet"
    # Born 1990 with no death: treated as living, so no dates or places leave the server.
    cara = rows["Cara Example"]
    assert cara["living"] and cara["start"] is None and cara["places"] == []
    assert data["living_private"] == 1
    # Ben, born 1880, is presumed dead: placed in time, but his death is unknown.
    ben = rows["Ben Example"]
    assert not ben["living"] and ben["start"]["earliest"] == 1880 and ben["end"] is None
    assert cara["parents"] == [ada["id"]]
    kinds = {o["kind"] for o in data["overlays"]}
    assert {"war", "records", "law", "calendar"} <= kinds
    ww1 = next(o for o in data["overlays"] if o["title"] == "First World War")
    assert (ww1["year_from"], ww1["year_to"]) == (1914, 1918) and ww1["source_url"]


def test_markers_and_preset(imported, alice_client, bob_client, project):
    url = f"/api/v1/projects/{project.id}/lifeline"
    r = alice_client.post(f"{url}/markers", {"title": "I was born", "year_from": 1985},
                          content_type=JSON)  # fmt: skip
    assert r.status_code == 201 and r.json()["kind"] == "custom"
    bad = alice_client.post(f"{url}/markers", {"title": "x", "year_from": 1990, "year_to": 1980},
                            content_type=JSON)  # fmt: skip
    assert bad.status_code == 422
    assert any(o["title"] == "I was born" for o in alice_client.get(url).json()["overlays"])
    # Markers stay in their project.
    other = Project.objects.create(owner=make_user("carol@example.com"), title="Other")
    assert not OverlayEvent.objects.filter(project=other).exists()
    # Someone without access can't add one, or see the Lifeline.
    assert bob_client.post(f"{url}/markers", {"title": "x", "year_from": 1900},
                           content_type=JSON).status_code == 404  # fmt: skip
    assert bob_client.get(url).status_code == 404
    saved = alice_client.put(f"{url}/preset", {"kinds": ["war", "nonsense", "war", "family"]},
                             content_type=JSON).json()  # fmt: skip
    assert saved["kinds"] == ["war", "family"]
    assert alice_client.get(url).json()["kinds"] == ["war", "family"]
    marker = OverlayEvent.objects.get(title="I was born")
    assert alice_client.delete(f"{url}/markers/{marker.id}").status_code == 204


def test_builtin_overlays_reload_cleanly():
    assert load_overlays() == load_overlays()
    assert OverlayEvent.objects.filter(project=None, key="census-1921").get().date_text == (
        "19 June 1921"
    )


def _row(start=None, end=None, places=(), living=False):
    def w(earliest, latest, c="exact"):
        return {"earliest": earliest, "latest": latest, "certainty": c, "text": "", "from": "birth"}

    return {
        "name": "X",
        "living": living,
        "start": w(*start) if start else None,
        "end": w(*end) if end else None,
        "places": list(places),
    }


def test_status_rules_match_the_page():
    from genealogy.lifeline import status_at, why_uncertain

    exact = _row((1900, 1900), (1980, 1980))
    about = _row((1845, 1855, "about"), (1920, 1920))
    no_death = _row((1880, 1880))
    assert [status_at(exact, y) for y in (1950, 1899, 1983, 2000)] == [
        "alive", "soon-born", "recently-died", "not-alive"
    ]  # fmt: skip
    assert status_at(about, 1850) == "uncertain" and why_uncertain(about, 1850) == "born about 1850"
    assert status_at(about, 1860) == "alive"
    assert status_at(no_death, 1950) == "uncertain"
    assert why_uncertain(no_death, 1950) == "death not recorded"
    assert status_at(_row(living=True), 1985) == "private"
    resident = _row(
        (1880, 1880), places=[{"kind": "residence", "year_from": 1921, "year_to": 1921}]
    )
    assert status_at(resident, 1915) == "alive" and status_at(resident, 1930) == "uncertain"


def test_assistant_lifeline_tool(imported, alice, bob, project):
    import json

    from assistant.tools import ToolKit

    kit = ToolKit(user=alice, project_id=project.id)
    out, error = kit.run("lifeline", {"year": 1900, "layers": ["war"]})
    data = json.loads(out)
    assert not error and data["project"] == "Example family"
    assert data["alive"] == ["Ada Example"]  # about 1850 to 1920; Ben born 1880 too:
    assert {"name": "Ben Example", "why": "death not recorded"} in data["possibly_alive"]
    assert data["living_not_counted"] == 1 and "Cara" not in out  # never named
    [cite] = kit.cited_in(f"[{data['cite']}]")
    assert cite["url"] == f"/projects/{project.id}/lifeline?year=1900&layers=war"
    # Someone else can't reach this tree, even by naming it.
    other = json.loads(ToolKit(user=bob).run("lifeline", {"year": 1900, "project": "Example"})[0])
    assert other["choose_project"] == [] and "no family tree" in other["note"]
    assert kit.run("lifeline", {"year": 99})[1] is True  # out of range
