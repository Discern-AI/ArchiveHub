"""Where to look next: records that could exist, who holds them, what they cost."""

import json
from datetime import date

import pytest
from django.contrib.contenttypes.models import ContentType

from assistant.tools import ToolKit
from genealogy.record_guide import record_office_for, where_to_look
from history.models import Assertion, LivingStatus, Person
from projects.models import Project

pytestmark = pytest.mark.django_db


def events(steps):
    return [(s.event, s.year) for s in steps]


def test_a_victorian_life_in_newbury():
    steps = where_to_look(
        {
            "birth": {"year": 1890, "place": "Newbury, Berkshire"},
            "death": {"year": 1952, "place": "Reading"},
        },
        record_office_for("Newbury, Berkshire"),
    )
    found = events(steps)
    assert ("birth", "1890") in found and ("death", "1952") in found
    assert [y for e, y in found if e == "census"] == ["1891", "1901", "1911", "1921"]
    assert ("1939 Register", "1939") in found and ("probate", "from 1952") in found
    birth = next(s for s in steps if s.event == "birth")
    gro = next(r for r in birth.routes if "GRO" in r.title)
    assert gro.access == "free" and "£3" in gro.cost and gro.checked
    baptism = next(s for s in steps if s.event == "baptism")
    assert baptism.routes[0].holder.startswith("Royal Berkshire Archives")
    census_1921 = next(s for s in steps if s.year == "1921")
    assert census_1921.routes[0].access == "paid" and "Manchester" in census_1921.routes[0].cost
    probate = next(s for s in steps if s.event == "probate")
    assert "£16" in probate.routes[0].cost


def test_before_civil_registration_points_to_the_church():
    steps = where_to_look(
        {"birth": {"year": 1820, "place": "Newbury"}, "death": {"year": 1850, "place": "Newbury"}}
    )
    found = events(steps)
    assert ("birth", "1820") not in found  # no civil registration yet
    assert ("death", "1850") in found
    assert [y for e, y in found if e == "census"] == ["1841"]
    baptism = next(s for s in steps if s.event == "baptism")
    assert "main record of a birth" in baptism.why
    assert not any(e == "military service" for e, _ in found)  # born too early for MOD records
    probate = next(s for s in steps if s.event == "probate")
    assert "church courts" in probate.why and not probate.routes[0].checked


def test_recent_births_are_outside_the_free_index():
    year = date.today().year - 90
    birth = where_to_look({"birth": {"year": year, "place": ""}})[0]
    gro = next(r for r in birth.routes if "GRO" in r.title)
    assert gro.access == "paid" and "certificate" in gro.cost


def test_scotland_has_its_own_routes():
    steps = where_to_look({"birth": {"year": 1870, "place": "Perth, Scotland"}})
    birth = steps[0]
    assert "Scotland" in birth.routes[0].title and "100 years" in birth.routes[0].cost
    baptism = next(s for s in steps if s.event == "baptism")
    assert "Scotland" in baptism.routes[0].title and not baptism.routes[0].checked
    assert all("Scotland" in s.routes[0].title for s in steps if s.event == "census")
    assert not any(s.event == "1939 Register" for s in steps)


def test_endpoint_only_for_people_who_have_died(alice, alice_client, bob_client):
    project = Project.objects.create(owner=alice, title="Synthetic family")
    ct = ContentType.objects.get_for_model(Person)

    def make(name, status, born):
        p = Person.objects.create(project=project, name=name, living_status=status)
        Assertion.objects.create(subject_type=ct, subject_id=p.id, predicate="birth date", value=str(born),
                                 year_from=born, year_to=born, project=project)  # fmt: skip
        Assertion.objects.create(subject_type=ct, subject_id=p.id, predicate="birth place",
                                 value="Newbury, Berkshire", project=project)  # fmt: skip
        return p

    dead = make("Arthur Example", LivingStatus.DECEASED, 1890)
    living = make("Alice Example", LivingStatus.LIVING, 1950)
    url = f"/api/v1/projects/{project.id}/people/{{}}/where-to-look"
    data = alice_client.get(url.format(dead.id)).json()
    assert any(s["event"] == "census" and s["year"] == "1891" for s in data["steps"])
    assert "may find nothing" in data["note"]
    data = alice_client.get(url.format(living.id)).json()
    assert data["steps"] == [] and "may be living" in data["note"]
    assert bob_client.get(url.format(dead.id)).status_code == 404


def test_assistant_tool_cites_checked_guidance():
    kit = ToolKit(user=None)
    content, is_error = kit.run("where_to_look", {"birth_year": 1890, "birth_place": "Newbury"})
    data = json.loads(content)
    assert not is_error and data["steps"][0]["event"] == "birth"
    gro = next(r for r in data["steps"][0]["routes"] if "GRO" in r["record"])
    cited = kit.cited_in(f"The GRO index is free [{gro['cite']}].")
    assert cited[0]["url"].startswith("https://www.gro.gov.uk/")
