"""The grader must pass good answers and catch bad ones, or the evals mean nothing."""

import json
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from assistant.evals.checks import grade

CASES = {
    c["id"]: c
    for c in json.loads(
        (Path(__file__).parents[1] / "assistant" / "evals" / "questions.json").read_text("utf-8")
    )
}
URLS = {"https://pubwiki.co.uk/x"}


def failed(case_id, answer, numbers=(1, 2, 3, 4), keys=()):
    checks = grade(CASES[case_id], answer, set(numbers), set(keys), URLS)
    return [c.name for c in checks if not c.passed]


def test_good_pigeons_answer_passes():
    answer = (
        "The sources disagree. Kelly's 1970 and the 1911 census give 5 Cheap Street [1, 2], "
        "while Closed Pubs gives 69 Cheap Street without a source [4]. Next, check old OS "
        "maps and the licensing records at Berkshire Record Office."
    )
    keys = {"pubwiki-kellys-1970", "closedpubs-pigeons"}
    assert failed("pigeons-address", answer, keys=keys) == []


def test_pigeons_answer_without_dispute_or_with_invented_citation_fails():
    answer = "It was at 5 Cheap Street and 69 [7]."
    problems = failed("pigeons-address", answer, keys={"pubwiki-kellys-1970"})
    assert "no invented citations" in problems
    assert "flags that sources disagree" in problems
    assert "cites closedpubs-pigeons" in problems


def test_invented_closure_date_fails():
    bad = "It was last listed in 1970 and closed in 1974."
    assert "avoids /closed (in|around|during|by) (the )?(19|20)\\d\\d/" in failed(
        "pigeons-closed", bad
    )
    good = "I couldn't find a closure date. The latest record is Kelly's 1970 [1]."
    assert failed("pigeons-closed", good) == []


def test_invented_link_fails():
    answer = "I couldn't find it. See https://made-up.example/golden-lion for more."
    assert "no invented links" in failed("unknown-pub", answer)
    ok = "I couldn't find any record of the Golden Lion in Reading. See https://pubwiki.co.uk/x."
    assert failed("unknown-pub", ok) == []


@pytest.mark.django_db
def test_run_evals_refuses_without_live_flag():
    with pytest.raises(CommandError, match="--live"):
        call_command("run_evals")
