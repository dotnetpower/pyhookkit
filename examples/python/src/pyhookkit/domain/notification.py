"""Provider-neutral notification value objects."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from urllib.parse import urlsplit

_EVENT_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_ALIAS = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

type MetadataValue = str


def _empty_metadata() -> Mapping[str, MetadataValue]:
    return {}


class Severity(StrEnum):
    """Canonical notification severity."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class MentionKind(StrEnum):
    """Provider-neutral mention target kind."""

    USER = "user"
    GROUP = "group"


@dataclass(frozen=True, slots=True)
class Fact:
    """An ordered key/value fact."""

    key: str
    value: str

    def __post_init__(self) -> None:
        _require_text("fact key", self.key, max_length=100)
        _require_text("fact value", self.value, max_length=1000)


@dataclass(frozen=True, slots=True)
class Link:
    """A labeled HTTPS destination."""

    label: str
    url: str

    def __post_init__(self) -> None:
        _require_text("link label", self.label, max_length=75)
        _require_https_url("link URL", self.url, max_length=2048)


@dataclass(frozen=True, slots=True)
class Image:
    """An external image with accessible fallback text."""

    url: str
    alt_text: str

    def __post_init__(self) -> None:
        _require_https_url("image URL", self.url, max_length=2048)
        _require_text("image alt text", self.alt_text, max_length=200)


@dataclass(frozen=True, slots=True)
class Mention:
    """A logical identity resolved inside a provider adapter."""

    kind: MentionKind
    alias: str

    def __post_init__(self) -> None:
        _require_text("mention alias", self.alias, max_length=100)
        if not _ALIAS.fullmatch(self.alias):
            raise ValueError("mention alias must use lower-case kebab-case")


@dataclass(frozen=True, slots=True)
class CanonicalNotification:
    """The immutable input shared by every provider renderer."""

    schema_version: str
    event_id: str
    route: str
    body: str
    severity: Severity
    title: str | None = None
    facts: tuple[Fact, ...] = ()
    links: tuple[Link, ...] = ()
    mentions: tuple[Mention, ...] = ()
    image: Image | None = None
    thread_key: str | None = None
    source_timestamp: datetime | None = None
    metadata: Mapping[str, MetadataValue] = field(default_factory=_empty_metadata)

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("schema version must be 1.0")
        _require_text("event ID", self.event_id, max_length=128)
        if not _EVENT_KEY.fullmatch(self.event_id):
            raise ValueError("event ID contains unsupported characters")
        _require_text("route", self.route, max_length=64)
        if not _ALIAS.fullmatch(self.route):
            raise ValueError("route must use lower-case kebab-case")
        _require_text("body", self.body, max_length=8000)
        if self.title is not None:
            _require_text("title", self.title, max_length=150)
        if len(self.facts) > 50:
            raise ValueError("facts must contain at most 50 items")
        if len(self.links) > 10:
            raise ValueError("links must contain at most 10 items")
        if len(self.mentions) > 20:
            raise ValueError("mentions must contain at most 20 items")
        if self.thread_key is not None:
            _require_text("thread key", self.thread_key, max_length=128)
            if not _EVENT_KEY.fullmatch(self.thread_key):
                raise ValueError("thread key contains unsupported characters")
        if (
            self.source_timestamp is not None
            and self.source_timestamp.utcoffset() is None
        ):
            raise ValueError("source timestamp must include a UTC offset")
        unknown_metadata = self.metadata.keys() - {"source", "correlationId"}
        if unknown_metadata:
            unknown = ", ".join(sorted(unknown_metadata))
            raise ValueError(f"unsupported metadata keys: {unknown}")
        for key, max_length in (("source", 64), ("correlationId", 128)):
            value = self.metadata.get(key)
            if value is not None:
                _require_text(f"metadata {key}", value, max_length=max_length)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def _require_text(field_name: str, value: str, *, max_length: int) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if len(value) > max_length:
        raise ValueError(f"{field_name} must not exceed {max_length} characters")


def _require_https_url(field_name: str, value: str, *, max_length: int) -> None:
    if len(value) > max_length:
        raise ValueError(f"{field_name} must not exceed {max_length} characters")
    parsed_url = urlsplit(value)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError(f"{field_name} must be an absolute HTTPS URL")
