"""Search across permitted content (SPEC §5, Search)."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from ninja import Router

from .queries import search_everything

router = Router()


@router.get("/search")
def search(request: HttpRequest, q: str = "", live: bool = False) -> dict[str, Any]:
    """`live=true` also asks outside sources; the search words are sent to them."""
    return search_everything(request.user, q[:200], live=live)
