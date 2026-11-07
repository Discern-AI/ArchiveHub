"""Search: covers permitted content only, and always says what was and wasn't searched."""

import pytest
from django.core.files.base import ContentFile
from django.test import Client
from django.utils import timezone

from archive.models import Derivative, FileAsset
from connectors.models import Dataset, DatasetRow
from history.loader import load_all
from history.models import Person, Source
from interviews.models import InterviewSession, Segment
from projects.models import Chat, Project
from search.queries import snippet
from timemap.models import MapItem

pytestmark = pytest.mark.django_db


@pytest.fixture
def ref(db):
    load_all()


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, title="Gran's Newbury")


def search(client, q):
    data = client.get("/api/v1/search", {"q": q}).json()
    return data, {g["key"]: g for g in data["groups"]}


def titles(group):
    return [r["title"] for r in group["results"]]


@pytest.fixture
def private_things(alice, project):
    FileAsset.objects.create(
        project=project,
        name="pigeons-letter.jpg",
        original=ContentFile(b"x", name="f"),
        size=1,
        sha256="0" * 64,
        kind="image",
        content_type="image/jpeg",
    )
    letter = FileAsset.objects.create(
        project=project,
        name="letter.pdf",
        original=ContentFile(b"x", name="g"),
        size=1,
        sha256="1" * 64,
        kind="pdf",
        content_type="application/pdf",
    )
    Derivative.objects.create(
        file=letter, kind="text", method="pdf_text", text="We met at the Pigeons in 1952."
    )
    chat = Chat.objects.create(owner=alice, project=project)
    session = InterviewSession.objects.create(
        chat=chat,
        narrator="Gran",
        consent_confirmed_by=alice,
        consent_confirmed_at=timezone.now(),
        consent_notice="notice",
    )
    Segment.objects.create(
        session=session, line=3, start_ms=0, end_ms=10, speaker="Gran", engine="fake",
        text="My father kept the Pigeons for a while after the war.",
    )  # fmt: skip
    MapItem.objects.create(
        project=project, kind="memory", title="Saturday job", text="Served at the Pigeons",
        latitude=51.4, longitude=-1.32, year_from=1952,
    )  # fmt: skip
    Person.objects.create(project=project, name="Ada Pigeonsworth", living_status="living")
    return session


def test_search_needs_login():
    assert Client().get("/api/v1/search", {"q": "Pigeons"}).status_code == 401


def test_public_results_and_what_was_searched(ref, alice_client):
    data, groups = search(alice_client, "Pigeons")
    assert data["words"] == ["pigeons"]
    assert "The Pigeons" in titles(groups["organisations"])
    assert any("Pigeons" in t for t in titles(groups["records"]))
    rec = groups["records"]["results"][0]
    assert rec["url"].startswith("https://") and rec["source"]
    for g in data["groups"]:
        assert g["searched"] and g["layer"] in ("public", "private")
    not_searched = {n["label"] for n in data["not_searched"]}
    assert {"Forum threads", "People and services"} <= not_searched


def test_every_word_must_match(ref, alice_client):
    _, groups = search(alice_client, "Cheap Street")
    assert "Cheap Street, Newbury" in titles(groups["places"])
    _, groups = search(alice_client, "Cheap Zanzibar")
    assert groups["places"]["count"] == 0


def test_no_results_still_says_what_was_searched(ref, alice_client):
    data, groups = search(alice_client, "zzqx")
    assert all(g["count"] == 0 for g in data["groups"])
    assert len(data["groups"]) >= 8 and data["not_searched"]


def test_empty_query(alice_client):
    data = alice_client.get("/api/v1/search", {"q": "  the "}).json()
    assert data["groups"] == [] and data["not_searched"]


def test_private_content_for_the_owner(ref, alice_client, project, private_things):
    _, groups = search(alice_client, "Pigeons")
    assert titles(groups["files"]) and all(
        r["project_title"] == "Gran's Newbury" for r in groups["files"]["results"]
    )
    assert set(titles(groups["files"])) == {"pigeons-letter.jpg", "letter.pdf"}
    pdf = next(r for r in groups["files"]["results"] if r["title"] == "letter.pdf")
    assert "Pigeons in 1952" in pdf["snippet"]
    line = groups["interviews"]["results"][0]
    assert line["title"] == "Gran, line 3"
    assert line["link"] == f"/interviews/{private_things.id}#line-3"
    assert titles(groups["map_items"]) == ["Saturday job"]
    assert groups["people"]["results"][0]["source"] == "Living: private"
    assert all(groups[k]["layer"] == "private" for k in ("files", "interviews", "people"))


def test_private_content_never_reaches_others(ref, bob_client, private_things):
    data, groups = search(bob_client, "Pigeons")
    for key in ("files", "interviews", "map_items", "people"):
        assert groups[key]["count"] == 0, key
    text = str(data)
    assert "letter.pdf" not in text and "Gran" not in text and "Saturday job" not in text


def test_old_map_names(ref, alice_client):
    ds = Dataset.objects.create(
        key="old-map-names", name="Old map names", source=Source.objects.get(key="gb1900")
    )
    DatasetRow.objects.create(
        dataset=ds, external_id="x1", title="CHEAP STREET", title_lower="cheap street",
        latitude=51.4005, longitude=-1.3231,
    )  # fmt: skip
    _, groups = search(alice_client, "cheap street")
    assert titles(groups["map_names"]) == ["CHEAP STREET"]


def test_counts_are_capped_and_paged(ref, alice_client, project):
    for n in range(12):
        MapItem.objects.create(
            project=project, kind="memory", title=f"Bakery visit {n}", text="bread",
            latitude=51.4, longitude=-1.32,
        )  # fmt: skip
    _, groups = search(alice_client, "bakery")
    g = groups["map_items"]
    assert g["count"] == 12 and len(g["results"]) == 8 and g["more"]


def test_snippet():
    text = "word " * 50 + "the Pigeons Inn " + "word " * 50
    s = snippet(text, ["pigeons"])
    assert "Pigeons" in s and s.startswith("…") and s.endswith("…") and len(s) < 220
    assert snippet("", ["x"]) == ""


@pytest.fixture
def live_sources(monkeypatch, settings):
    """Every outside source answers from a stand-in; one fails and one is slow."""
    import time

    from connectors.base import ConnectorRecord, Page, Unavailable
    from connectors.sources import CONNECTORS
    from search import queries

    settings.TNA_DISCOVERY_ENABLED = False
    sent = []

    def answer(key):
        def search(query, cursor=None, page_size=25):
            sent.append((key, query))
            if key == "historic-england":
                raise Unavailable("down")
            if key == "openalex":
                time.sleep(0.5)
            record = ConnectorRecord(
                connector=key, id="1", title=f"{key} result", url="https://example.org/1"
            )
            return Page(records=[record], next_cursor="x", searched=f"{key} for {query}")

        return search

    for key in queries.LIVE_SEARCH:
        monkeypatch.setattr(CONNECTORS[key], "search", answer(key))
    monkeypatch.setattr(queries, "LIVE_TIMEOUT", 0.3)
    return sent


def test_outside_sources_only_when_asked(ref, alice_client, live_sources):
    data, groups = search(alice_client, "Pigeons")
    assert not any(k.startswith("live:") for k in groups) and live_sources == []
    assert data["not_searched"][0]["label"].startswith("Outside sources")


def test_outside_sources_say_what_happened(ref, alice_client, live_sources):
    data = alice_client.get("/api/v1/search", {"q": "Pigeons Newbury", "live": "true"}).json()
    groups = {g["key"]: g for g in data["groups"]}
    gazette = groups["live:the-gazette"]
    assert gazette["live"] and gazette["count"] == 1 and gazette["more"]
    assert gazette["results"][0]["url"] == "https://example.org/1"
    assert groups["live:historic-england"]["error"] == "This source isn't responding right now."
    assert groups["live:openalex"]["error"] == "Didn't answer in time."
    not_searched = {n["label"] for n in data["not_searched"]}
    assert "The National Archives: Discovery" in not_searched  # not set up here
    assert not any(n.startswith("Outside sources") for n in not_searched)
    assert ("the-gazette", "Pigeons Newbury") in live_sources
