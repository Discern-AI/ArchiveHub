"""WP12: Explain this record, and Life and times."""

import pytest

from genealogy.models import Explanation, OverlayEvent
from genealogy.overlays import load_overlays
from projects.models import Project

pytestmark = pytest.mark.django_db
JSON = "application/json"
RECORD = "1881. William Spracklen, aged 9, admitted to the Union Workhouse. Discharged 1883."


def explain(client, **body):
    return client.post("/api/v1/explain", body, content_type=JSON)


def test_a_workhouse_record_gets_all_four_layers_with_sources(alice_client):
    r = explain(alice_client, text=RECORD, year=1881, place="Hungerford, Berkshire").json()
    assert r["says"]["text"] == RECORD  # 1. exactly as written
    terms = {w["term"]: w for w in r["words"]}  # 2. what the words mean
    assert {"Workhouse", "Admitted and discharged (workhouse)"} <= set(terms)
    wh = terms["Workhouse"]
    assert wh["applies"] and "1834" in wh["meaning"] and "1930" in wh["meaning"]
    assert all(s["url"].startswith("https://www.nationalarchives.gov.uk/") for s in wh["sources"])
    # 3. careful readings, labelled, never about this family in particular.
    assert r["may_mean"] and "doesn't say why" in r["may_mean"][0]["text"]
    assert "not what happened to this person" in r["may_mean_label"]
    # 4. where to find out more, including the local record office.
    more = " ".join(m["text"] for m in r["find_out_more"])
    assert "Admission and discharge books" in more and "census" in more and "MH 12" in more
    assert "Eton union's workhouse was in Slough" in more
    assert "Royal Berkshire Archives" in more
    assert r["sensitive"] and "Descendants decide" in r["sensitive_note"]


def test_a_record_from_before_1834_is_explained_as_it_was_then(alice_client):
    r = explain(
        alice_client, text="Mary Smith, a pauper, removed to the workhouse", year=1790
    ).json()
    wh = next(w for w in r["words"] if w["term"] == "Workhouse")
    assert not wh["applies"] and "Before 1834" in wh["period_note"]
    assert all(m["term"] != "Workhouse" for m in r["may_mean"])  # the union reading doesn't apply
    more = " ".join(m["text"] for m in r["find_out_more"])
    assert "overseers' accounts" in more and "Admission and discharge books" not in more


def test_unknown_words_and_bad_input(alice_client, client):
    r = explain(alice_client, text="Something entirely ordinary").json()
    assert r["nothing_found"] and "offer an explanation" in r["note"]
    assert explain(alice_client, text="  ").status_code == 422
    assert explain(alice_client, text="x", year=50).status_code == 422
    assert explain(client, text=RECORD).status_code == 401


def test_offered_explanations_show_with_credit_once_reviewed(alice_client, bob_client):
    body = {"term": "Cordwainer", "meaning": "A shoemaker working new leather.",
            "credit": "Bob, Berkshire FHS", "sources": []}  # fmt: skip
    assert bob_client.post("/api/v1/explanations", body, content_type=JSON).status_code == 422
    body["sources"] = [{"title": "A dictionary of old trades", "url": ""}]
    r = bob_client.post("/api/v1/explanations", body, content_type=JSON)
    assert r.status_code == 201 and r.json()["status"] == "proposed"
    text = "John Smith, cordwainer, of Newbury"
    assert explain(alice_client, text=text).json()["nothing_found"]  # not reviewed yet
    Explanation.objects.update(status="reviewed")
    words = explain(alice_client, text=text).json()["words"]
    assert words[0]["term"] == "Cordwainer" and words[0]["contributed_by"] == "Bob, Berkshire FHS"
    assert bob_client.get("/api/v1/explanations/mine").json()[0]["status"] == "Reviewed"


def test_life_and_times_is_context_with_sources(alice_client, alice):
    load_overlays()
    r = alice_client.get("/api/v1/life-and-times", {"year": 1900}).json()
    assert "not a fact about anyone" in r["label"]
    m = r["money"]
    assert m["available"] and m["multiplier"] > 100 and "£1 in 1900" in m["sentence"]
    assert "not of wages" in m["note"] and "Office for National Statistics" in m["source"]
    w = r["weather"]
    assert w["available"] and "In central England, 1900 averaged" in w["sentence"]
    assert "Lancashire, London and Bristol" in w["note"] and "HadCET" in w["source"]
    happening = {h["title"]: h for h in r["happening"]}
    assert happening["Boer War"]["when"] == "under way"
    assert happening["Poor law unions created"]["when"] == "in force since 1834"
    assert "Census" not in happening  # only in a census year
    assert "Census" in {h["title"] for h in alice_client.get(
        "/api/v1/life-and-times", {"year": 1901}).json()["happening"]}  # fmt: skip
    early = alice_client.get("/api/v1/life-and-times", {"year": 1790}).json()
    assert not early["money"]["available"] and "starts in 1800" in early["money"]["note"]
    assert early["weather"]["available"]
    cold = alice_client.get("/api/v1/life-and-times", {"year": 1740}).json()["weather"]
    assert cold["rank"].startswith("One of the coldest years on record")
    # A project's own marker shows for its members only.
    project = Project.objects.create(owner=alice, title="Mine")
    OverlayEvent.objects.create(project=project, kind="custom", title="Gran born", year_from=1900)
    mine = alice_client.get("/api/v1/life-and-times", {"year": 1900, "project_id": project.id})
    assert "Gran born" in {h["title"] for h in mine.json()["happening"]}
