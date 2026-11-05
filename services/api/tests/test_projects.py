import pytest

from core.models import AuditLog
from projects.models import Chat, Message, Project, ProjectMember, Role

JSON = "application/json"


@pytest.mark.django_db
def test_project_crud(alice_client, alice):
    r = alice_client.post("/api/v1/projects", {"title": "  The Pigeons  "}, content_type=JSON)
    assert r.status_code == 201
    project = r.json()
    assert project["title"] == "The Pigeons"
    assert project["visibility"] == "private"
    assert project["is_owner"] is True

    pid = project["id"]
    assert [p["id"] for p in alice_client.get("/api/v1/projects").json()] == [pid]

    r = alice_client.patch(f"/api/v1/projects/{pid}", {"summary": "A lost pub"}, content_type=JSON)
    assert r.json()["summary"] == "A lost pub"

    assert alice_client.delete(f"/api/v1/projects/{pid}").status_code == 204
    assert not Project.objects.exists()
    actions = set(AuditLog.objects.values_list("action", flat=True))
    assert actions == {"project.create", "project.update", "project.delete"}


@pytest.mark.django_db
def test_empty_title_rejected(alice_client):
    r = alice_client.post("/api/v1/projects", {"title": "   "}, content_type=JSON)
    assert r.status_code == 422


@pytest.mark.django_db
def test_other_users_cannot_see_or_change_projects(alice, bob_client):
    project = Project.objects.create(owner=alice, title="Private")
    chat = Chat.objects.create(owner=alice, project=project)
    Message.objects.create(chat=chat, role="user", content="secret")

    assert bob_client.get("/api/v1/projects").json() == []
    assert bob_client.get(f"/api/v1/projects/{project.id}").status_code == 404
    r = bob_client.patch(f"/api/v1/projects/{project.id}", {"title": "x"}, content_type=JSON)
    assert r.status_code == 404
    assert bob_client.delete(f"/api/v1/projects/{project.id}").status_code == 404
    assert bob_client.get("/api/v1/chats").json() == []
    assert bob_client.get(f"/api/v1/chats/{chat.id}").status_code == 404
    assert bob_client.get(f"/api/v1/chats/{chat.id}/messages").status_code == 404
    r = bob_client.post("/api/v1/chats", {"project_id": str(project.id)}, content_type=JSON)
    assert r.status_code == 404


@pytest.mark.django_db
def test_viewer_can_read_but_not_edit(alice, bob, bob_client):
    project = Project.objects.create(owner=alice, title="Shared")
    ProjectMember.objects.create(project=project, user=bob, role=Role.VIEWER)

    assert bob_client.get(f"/api/v1/projects/{project.id}").json()["is_owner"] is False
    r = bob_client.patch(f"/api/v1/projects/{project.id}", {"title": "x"}, content_type=JSON)
    assert r.status_code == 404
    r = bob_client.post("/api/v1/chats", {"project_id": str(project.id)}, content_type=JSON)
    assert r.status_code == 404


@pytest.mark.django_db
def test_editor_cannot_delete(alice, bob, bob_client):
    project = Project.objects.create(owner=alice, title="Shared")
    ProjectMember.objects.create(project=project, user=bob, role=Role.EDITOR)
    r = bob_client.patch(f"/api/v1/projects/{project.id}", {"title": "Renamed"}, content_type=JSON)
    assert r.status_code == 200
    assert bob_client.delete(f"/api/v1/projects/{project.id}").status_code == 404


@pytest.mark.django_db
def test_chats_loose_and_in_project(alice_client):
    loose = alice_client.post("/api/v1/chats", {}, content_type=JSON).json()
    assert loose["project_id"] is None

    pid = alice_client.post("/api/v1/projects", {"title": "P"}, content_type=JSON).json()["id"]
    in_project = alice_client.post("/api/v1/chats", {"project_id": pid}, content_type=JSON).json()

    all_ids = {c["id"] for c in alice_client.get("/api/v1/chats").json()}
    assert all_ids == {loose["id"], in_project["id"]}
    filtered = alice_client.get(f"/api/v1/chats?project_id={pid}").json()
    assert [c["id"] for c in filtered] == [in_project["id"]]
