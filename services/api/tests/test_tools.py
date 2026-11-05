import json

import pytest

from assistant.tools import ToolKit, tool_definitions
from history.loader import load_all

pytestmark = pytest.mark.django_db


@pytest.fixture
def kit(alice):
    load_all()
    return ToolKit(user=alice)


def run(kit, name, args):
    out, is_error = kit.run(name, args)
    return json.loads(out), is_error


def test_definitions_are_stable_and_well_formed():
    first, second = tool_definitions(), tool_definitions()
    assert first == second  # constant across requests (prompt caching, thinking blocks)
    for tool in first:
        assert tool["input_schema"]["additionalProperties"] is False
        assert tool["description"]


def test_compare_claims_numbers_evidence_and_logs_dispute(kit):
    result, is_error = run(kit, "compare_claims", {"subject": "Pigeons", "predicate": "address"})
    assert not is_error and result["found"]
    (question,) = result["questions"]
    assert question["sources_disagree"] is True
    cites = {e["cite"] for a in question["answers"] for e in a["evidence"]}
    assert cites == set(range(1, len(cites) + 1))
    assert any("sources disagree on address" in c["text"] for c in kit.checked)


def test_unknown_subject_is_reported_not_invented(kit):
    result, _ = run(kit, "compare_claims", {"subject": "The Golden Lion, Reading"})
    assert result["found"] is False
    assert kit.checked[-1]["status"] == "Not found"


def test_directory_logs_sources_it_cannot_reach(kit):
    result, _ = run(kit, "search_source_directory", {"query": "newspapers"})
    assert result["results"]
    assert any(c["status"] == "Couldn't access" for c in kit.checked)


def test_get_record_needs_a_real_id(kit):
    result, _ = run(kit, "get_record", {"record_id": "not-an-id"})
    assert "error" in result
    records, _ = run(kit, "search_records", {"query": "Catherine Wheel"})
    detail, _ = run(kit, "get_record", {"record_id": records["results"][0]["record_id"]})
    assert detail["fields"] and detail["url"].startswith("https://")


def test_invalid_input_is_an_error_result(kit):
    out, is_error = kit.run("search_records", {"query": "", "surprise": True})
    assert is_error and "INVALID_INPUT" in out
    out, is_error = kit.run("drop_tables", {})
    assert is_error


def test_only_numbers_a_tool_returned_become_sources(kit):
    run(kit, "compare_claims", {"subject": "Pigeons", "predicate": "address"})
    sources = kit.cited_in("It was at 5 Cheap Street [1, 2] or 69 [4]. See also [99] and [0].")
    assert [s["n"] for s in sources] == [1, 2, 4]
    assert all(s["url"].startswith("https://") for s in sources)
    assert kit.cited_in("No citations here.") == []
