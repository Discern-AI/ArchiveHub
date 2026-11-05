"""The shared connector interface (SPEC §9). The Explorer and the assistant use only this,
so a new source never needs its own screen."""

from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

# --- Errors every connector maps its failures onto ----------------------------------


class ConnectorError(Exception):
    kind = "error"
    user_message = "This source couldn't be searched."


class Unavailable(ConnectorError):
    kind = "unavailable"
    user_message = "This source isn't responding right now."


class RateLimited(ConnectorError):
    kind = "rate_limited"
    user_message = "This source is limiting requests. Try again shortly."


class AccessDenied(ConnectorError):
    kind = "access_denied"
    user_message = "ArchiveHub doesn't have access to this source."


class NotFound(ConnectorError):
    kind = "not_found"
    user_message = "That record wasn't found."


class BadQuery(ConnectorError):
    kind = "bad_query"
    user_message = "That search couldn't be run."


# --- Normalised records ------------------------------------------------------------


@dataclass
class ConnectorRecord:
    """A record in the common shape. Provider-specific details stay in `fields`."""

    connector: str
    id: str
    title: str
    description: str = ""
    record_type: str = ""
    url: str = ""
    date_text: str = ""
    latitude: float | None = None
    longitude: float | None = None
    fields: dict[str, Any] = field(default_factory=dict)
    rights: str = ""
    attribution: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Page:
    records: list[ConnectorRecord]
    next_cursor: str | None = None
    searched: str = ""  # plain description of what was searched, for "What I checked"


def encode_cursor(data: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> dict[str, Any]:
    if not cursor:
        return {}
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError) as exc:
        raise BadQuery("Invalid cursor") from exc
    if not isinstance(data, dict):
        raise BadQuery("Invalid cursor")
    return data


class SourceConnector:
    """Base class. Subclasses set the class attributes and implement search/get_record."""

    key: ClassVar[str]
    name: ClassVar[str]
    source_key: ClassVar[str]  # the history.Source directory entry
    access_type: ClassVar[str]  # hosted | live_api | metadata | external_only
    capabilities: ClassVar[frozenset[str]] = frozenset({"search", "record_detail"})
    licence: ClassVar[str] = ""
    attribution: ClassVar[str] = ""
    storage: ClassVar[str] = "reference_only"  # full_copy | metadata_only | reference_only
    description: ClassVar[str] = ""
    max_page_size: ClassVar[int] = 50

    def search(self, query: str, cursor: str | None = None, page_size: int = 25) -> Page:
        raise NotImplementedError

    def get_record(self, record_id: str) -> ConnectorRecord:
        raise NotImplementedError

    def citation(self, record: ConnectorRecord) -> str:
        parts = [record.title, self.name]
        if self.attribution:
            parts.append(self.attribution)
        return ". ".join(p for p in parts if p)

    def storage_policy(self, record: ConnectorRecord) -> str:
        return self.storage

    def describe(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "access_type": self.access_type,
            "capabilities": sorted(self.capabilities),
            "licence": self.licence,
            "attribution": self.attribution,
            "storage": self.storage,
        }
