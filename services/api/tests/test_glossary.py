"""Checked explanations of old terms and map abbreviations."""

import json

import pytest

from assistant.tools import ToolKit
from history.glossary import DATA, abbreviation, search_terms

pytestmark = pytest.mark.django_db


def test_every_entry_has_a_checked_source():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for t in data["terms"]:
        assert t["meaning"] and t["checked_on"] and t["sources"]
        assert all(s["url"].startswith("https://") for s in t["sources"])
    for a in data["abbreviations"]:
        assert a["meanings"] and a["source_url"].startswith("https://maps.nls.uk/os/abbrev/")


def test_abbreviations_give_every_meaning():
    assert abbreviation("P.H.")["text"] == "public house"
    sp = abbreviation("S.Ps")
    assert (
        sp["plural"] and sp["meanings"][0] == "signal post" and sp["text"].startswith("could be:")
    )
    assert abbreviation("GP")["meanings"] == ["gas plug", "guide post (signpost)"]
    assert abbreviation("Ch")["text"] == "church" and "coach house" in abbreviation("CH")["text"]
    assert abbreviation("Smithy") is None and abbreviation("") is None


def test_terms_match_whole_names_best():
    assert [t["key"] for t in search_terms("settlement examination")][0] == "settlement-examination"
    assert [t["key"] for t in search_terms("what is a farthing")] == ["farthing"]
    assert [t["key"] for t in search_terms("9/6")] == ["lsd"]
    assert search_terms("Newbury pubs") == []


def test_assistant_explains_with_citations():
    kit = ToolKit(user=None)
    content, is_error = kit.run("explain_term", {"term": "guinea"})
    data = json.loads(content)
    assert not is_error and data["explanations"][0]["meaning"].startswith(
        "One pound and one shilling"
    )
    cited = kit.cited_in(f"A guinea was 21 shillings [{data['explanations'][0]['cite']}].")
    assert cited[0]["url"].startswith("https://www.nottingham.ac.uk/")
    content, _ = kit.run("explain_term", {"term": "zzqx"})
    assert json.loads(content)["explanations"] == []
    assert kit.checked[-1]["status"] == "Not found"


def test_search_includes_explanations(alice_client):
    groups = {
        g["key"]: g for g in alice_client.get("/api/v1/search", {"q": "guinea"}).json()["groups"]
    }
    assert groups["explanations"]["results"][0]["title"] == "Guinea"
    groups = {g["key"]: g for g in alice_client.get("/api/v1/search", {"q": "PH"}).json()["groups"]}
    assert groups["explanations"]["results"][0]["snippet"] == "Public house"
