import pytest
from django.test import AsyncClient, Client

from accounts.models import User


@pytest.fixture(autouse=True)
def _test_settings(settings, tmp_path):
    settings.ASSISTANT_PROVIDER = "fake"
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.JOBS_BACKEND = "sync"
    settings.SPEECH_PROVIDER = "fake"
    settings.MEDIA_ROOT = str(tmp_path / "media")


def make_user(email: str) -> User:
    return User.objects.create_user(email=email, password="correct-horse-battery")


@pytest.fixture
def alice(db) -> User:
    return make_user("alice@example.com")


@pytest.fixture
def bob(db) -> User:
    return make_user("bob@example.com")


@pytest.fixture
def alice_client(alice) -> Client:
    c = Client()
    c.force_login(alice)
    return c


@pytest.fixture
def bob_client(bob) -> Client:
    c = Client()
    c.force_login(bob)
    return c


@pytest.fixture
def alice_async(alice) -> AsyncClient:
    c = AsyncClient()
    c.force_login(alice)
    return c
