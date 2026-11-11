from django.http import HttpRequest
from django.middleware.csrf import get_token
from ninja import NinjaAPI
from ninja.security import django_auth

from archive.api import router as archive_router
from culture.api import router as culture_router
from explorer.api import router as explorer_router
from genealogy.api import router as genealogy_router
from interviews.api import router as interviews_router
from lineages.api import router as lineages_router
from projects.api import router as projects_router
from publishing.api import router as publishing_router
from search.api import router as search_router
from timemap.api import router as timemap_router

# django_auth is session-cookie auth; Ninja enforces CSRF on unsafe methods with it.
api = NinjaAPI(title="ArchiveHub API", version="1", auth=django_auth)
api.add_router("", projects_router)
api.add_router("", explorer_router)
api.add_router("", archive_router)
api.add_router("", genealogy_router)
api.add_router("", interviews_router)
api.add_router("", timemap_router)
api.add_router("", lineages_router)
api.add_router("", culture_router)
api.add_router("", publishing_router)
api.add_router("", search_router)


@api.get("/health", auth=None)
def health(request: HttpRequest) -> dict:
    return {"status": "ok"}


@api.get("/csrf", auth=None)
def csrf(request: HttpRequest) -> dict:
    """Sets the csrftoken cookie so the browser app can send it on unsafe requests."""
    get_token(request)
    return {"ok": True}
