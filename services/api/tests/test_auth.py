import pytest
from django.test import Client

from accounts.models import Profile, User

AUTH = "/_allauth/browser/v1/auth"


@pytest.mark.django_db
def test_signup_login_logout_flow():
    c = Client()
    r = c.post(
        f"{AUTH}/signup",
        {"email": "new@example.com", "password": "a-long-unusual-password"},
        content_type="application/json",
    )
    assert r.status_code == 200, r.content
    user = User.objects.get(email="new@example.com")
    assert Profile.objects.filter(user=user, visibility="private").exists()

    assert c.get("/api/v1/me").json()["email"] == "new@example.com"

    r = c.delete(f"{AUTH}/session")
    assert r.status_code == 401  # allauth reports "no longer authenticated"
    assert c.get("/api/v1/me").status_code == 401

    r = c.post(
        f"{AUTH}/login",
        {"email": "new@example.com", "password": "a-long-unusual-password"},
        content_type="application/json",
    )
    assert r.status_code == 200
    assert c.get("/api/v1/me").status_code == 200


@pytest.mark.django_db
def test_wrong_password_rejected(alice):
    r = Client().post(
        f"{AUTH}/login",
        {"email": alice.email, "password": "wrong"},
        content_type="application/json",
    )
    assert r.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/api/v1/me", "/api/v1/projects", "/api/v1/chats"])
def test_api_requires_login(path):
    assert Client().get(path).status_code == 401


@pytest.mark.django_db
def test_health_is_public():
    assert Client().get("/api/v1/health").json() == {"status": "ok"}


@pytest.mark.django_db
def test_unsafe_requests_need_csrf_token(alice):
    c = Client(enforce_csrf_checks=True)
    c.force_login(alice)
    r = c.post("/api/v1/projects", {"title": "No token"}, content_type="application/json")
    assert r.status_code == 403

    c.get("/api/v1/csrf")
    token = c.cookies["csrftoken"].value
    r = c.post(
        "/api/v1/projects",
        {"title": "With token"},
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    assert r.status_code == 201
