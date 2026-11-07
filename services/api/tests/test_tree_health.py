"""Tree health check: points out things to look at; never changes anything.

All people here are fictional.
"""

import pytest
from django.contrib.contenttypes.models import ContentType

from genealogy.health import check_tree
from genealogy.models import RelationKind, Relationship
from history.models import Assertion, LivingStatus, Person
from projects.models import Project

pytestmark = pytest.mark.django_db


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, title="Synthetic family")


def person(project, name, sex="", born=None, died=None, method="import"):
    p = Person.objects.create(
        project=project, name=name, sex=sex, living_status=LivingStatus.DECEASED
    )
    ct = ContentType.objects.get_for_model(Person)
    for predicate, year in (("birth date", born), ("death date", died)):
        if year is not None:
            Assertion.objects.create(
                subject_type=ct, subject_id=p.id, predicate=predicate, value=str(year),
                year_from=year, year_to=year, project=project, method=method,
            )  # fmt: skip
    return p


def parent(project, p, child):
    Relationship.objects.create(project=project, person=p, relative=child, kind=RelationKind.PARENT)


def titles(result):
    return [f["title"] for f in result["findings"]]


def test_a_clean_family_has_no_findings(project):
    dad = person(project, "John Example", "M", 1850, 1910)
    mum = person(project, "Mary Example", "F", 1852, 1920)
    kid = person(project, "Ann Example", "F", 1880, 1950)
    parent(project, dad, kid)
    parent(project, mum, kid)
    result = check_tree(project)
    assert result["findings"] == [] and result["people"] == 3 and result["branches"] == 1


def test_date_and_parent_problems(project):
    dad = person(project, "John Example", "M", 1850, 1870)
    mum = person(project, "Mary Example", "F", 1870, 1860)  # died before born
    kid = person(project, "Ann Example", "F", 1878)  # born after both parents died
    young = person(project, "Young Parent", "F", 1875)
    parent(project, dad, kid)
    parent(project, mum, kid)
    parent(project, young, kid)
    found = check_tree(project)["findings"]
    assert "Died before being born" in [f["title"] for f in found]
    after = [f for f in found if f["title"] == "Born after a parent's death"]
    assert {f["people"][0]["name"] for f in after} == {"John Example", "Mary Example"}
    young_finding = next(
        f for f in found
        if f["title"] == "Very young parent" and f["people"][0]["name"] == "Young Parent"
    )  # fmt: skip
    assert "at most 3" in young_finding["detail"]


def test_father_may_die_shortly_before_a_birth(project):
    dad = person(project, "John Example", "M", 1850, 1879)
    kid = person(project, "Ann Example", "F", 1880)
    parent(project, dad, kid)
    assert "Born after a parent's death" not in titles(check_tree(project))


def test_possible_duplicates_are_only_flagged(project):
    a = person(project, "William Carter", "M", 1780)
    b = person(project, "William  CARTER", "M", 1781)
    person(project, "William Carter", "M", 1820)  # too far apart
    found = [f for f in check_tree(project)["findings"] if f["kind"] == "duplicates"]
    assert len(found) == 1 and {p["id"] for p in found[0]["people"]} == {str(a.id), str(b.id)}
    assert "only a person can decide" in found[0]["detail"]
    assert Person.objects.filter(project=project).count() == 3  # nothing merged


def test_corrections_are_what_get_checked(project):
    p = person(project, "Mary Example", "F", 1870, 1860)
    ct = ContentType.objects.get_for_model(Person)
    Assertion.objects.create(
        subject_type=ct, subject_id=p.id, predicate="death date", value="1930",
        year_from=1930, year_to=1930, project=project, method="user",
    )  # fmt: skip
    assert "Died before being born" not in titles(check_tree(project))


def test_separate_branches_and_gaps(project):
    a = person(project, "John Example", "M", 1850)
    b = person(project, "Ann Example", "F", 1880)
    parent(project, a, b)
    person(project, "Loose Person", "M")
    result = check_tree(project)
    assert result["branches"] == 2
    assert "Not connected to anyone" in titles(result)
    assert any(t.endswith("people with no dates") for t in titles(result))


def test_endpoint_is_private_to_the_project(project, alice_client, bob_client):
    person(project, "Mary Example", "F", 1870, 1860)
    url = f"/api/v1/projects/{project.id}/tree-health"
    data = alice_client.get(url).json()
    assert (
        data["findings"][0]["title"] == "Died before being born"
        and "Nothing has been changed" in data["note"]
    )
    assert bob_client.get(url).status_code == 404
