"""Strict canonical notification JSON input parsing."""

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import cast

from pyhookkit.domain.notification import (
    CanonicalNotification,
    Fact,
    Image,
    Link,
    Mention,
    MentionKind,
    Severity,
)

_TOP_LEVEL_FIELDS = {
    "schemaVersion",
    "eventId",
    "route",
    "title",
    "body",
    "severity",
    "facts",
    "links",
    "mentions",
    "image",
    "threadKey",
    "sourceTimestamp",
    "metadata",
}
_FACT_FIELDS = {"key", "value"}
_LINK_FIELDS = {"label", "url"}
_MENTION_FIELDS = {"kind", "alias"}
_IMAGE_FIELDS = {"url", "altText"}
_METADATA_FIELDS = {"source", "correlationId"}


class CanonicalNotificationJsonError(ValueError):
    """A canonical notification JSON payload is malformed."""


def load_canonical_notification(path: Path) -> CanonicalNotification:
    """Load one canonical notification from a JSON file."""
    with path.open(encoding="utf-8") as file:
        value: object = json.load(file)
    return canonical_notification_from_json(value, source_name=str(path))


def canonical_notification_from_json(
    value: object,
    *,
    source_name: str = "notification",
) -> CanonicalNotification:
    """Convert validated contract JSON into a canonical domain notification."""
    payload = _require_object(source_name, value)
    _reject_unknown_fields(source_name, payload, _TOP_LEVEL_FIELDS)

    facts = tuple(
        _parse_fact(item, f"{source_name}.facts[{index}]")
        for index, item in enumerate(
            _optional_array(source_name, payload, "facts") or ()
        )
    )
    links = tuple(
        _parse_link(item, f"{source_name}.links[{index}]")
        for index, item in enumerate(
            _optional_array(source_name, payload, "links") or ()
        )
    )
    mentions = tuple(
        _parse_mention(item, f"{source_name}.mentions[{index}]")
        for index, item in enumerate(
            _optional_array(source_name, payload, "mentions") or ()
        )
    )
    image = (
        _parse_image(
            payload["image"],
            f"{source_name}.image",
        )
        if "image" in payload
        else None
    )
    source_timestamp = _parse_timestamp(
        _optional_string(source_name, payload, "sourceTimestamp"),
        field_name=f"{source_name}.sourceTimestamp",
    )
    metadata: Mapping[str, str]
    if "metadata" in payload:
        metadata = _parse_metadata(
            payload["metadata"],
            f"{source_name}.metadata",
        )
    else:
        metadata = {}

    try:
        severity = Severity(_require_string(source_name, payload, "severity"))
    except ValueError as error:
        raise CanonicalNotificationJsonError(
            f"{source_name}.severity must be one of: info, success, warning, error"
        ) from error

    try:
        return CanonicalNotification(
            schema_version=_require_string(source_name, payload, "schemaVersion"),
            event_id=_require_string(source_name, payload, "eventId"),
            route=_require_string(source_name, payload, "route"),
            title=_optional_string(source_name, payload, "title"),
            body=_require_string(source_name, payload, "body"),
            severity=severity,
            facts=facts,
            links=links,
            mentions=mentions,
            image=image,
            thread_key=_optional_string(source_name, payload, "threadKey"),
            source_timestamp=source_timestamp,
            metadata=metadata,
        )
    except ValueError as error:
        raise CanonicalNotificationJsonError(str(error)) from error


def _parse_fact(value: object, field_name: str) -> Fact:
    payload = _require_object(field_name, value)
    _reject_unknown_fields(field_name, payload, _FACT_FIELDS)
    try:
        return Fact(
            _require_string(field_name, payload, "key"),
            _require_string(field_name, payload, "value"),
        )
    except ValueError as error:
        raise CanonicalNotificationJsonError(str(error)) from error


def _parse_link(value: object, field_name: str) -> Link:
    payload = _require_object(field_name, value)
    _reject_unknown_fields(field_name, payload, _LINK_FIELDS)
    try:
        return Link(
            _require_string(field_name, payload, "label"),
            _require_string(field_name, payload, "url"),
        )
    except ValueError as error:
        raise CanonicalNotificationJsonError(str(error)) from error


def _parse_mention(value: object, field_name: str) -> Mention:
    payload = _require_object(field_name, value)
    _reject_unknown_fields(field_name, payload, _MENTION_FIELDS)
    kind_value = _require_string(field_name, payload, "kind")
    try:
        kind = MentionKind(kind_value)
    except ValueError as error:
        raise CanonicalNotificationJsonError(
            f"{field_name}.kind must be one of: user, group"
        ) from error
    try:
        return Mention(
            kind,
            _require_string(field_name, payload, "alias"),
        )
    except ValueError as error:
        raise CanonicalNotificationJsonError(str(error)) from error


def _parse_image(value: object, field_name: str) -> Image:
    payload = _require_object(field_name, value)
    _reject_unknown_fields(field_name, payload, _IMAGE_FIELDS)
    try:
        return Image(
            _require_string(field_name, payload, "url"),
            _require_string(field_name, payload, "altText"),
        )
    except ValueError as error:
        raise CanonicalNotificationJsonError(str(error)) from error


def _parse_metadata(value: object, field_name: str) -> Mapping[str, str]:
    payload = _require_object(field_name, value)
    _reject_unknown_fields(field_name, payload, _METADATA_FIELDS)
    metadata: dict[str, str] = {}
    for key in sorted(payload):
        metadata[key] = _require_string(field_name, payload, key)
    return metadata


def _parse_timestamp(value: str | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise CanonicalNotificationJsonError(
            f"{field_name} must be an ISO 8601 timestamp with a UTC offset"
        ) from error
    if timestamp.utcoffset() is None:
        raise CanonicalNotificationJsonError(
            f"{field_name} must be an ISO 8601 timestamp with a UTC offset"
        )
    return timestamp


def _optional_array(
    parent_name: str,
    payload: Mapping[str, object],
    key: str,
) -> Sequence[object] | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, list):
        raise CanonicalNotificationJsonError(f"{parent_name}.{key} must be an array")
    return cast(list[object], value)


def _optional_string(
    parent_name: str,
    payload: Mapping[str, object],
    key: str,
) -> str | None:
    if key not in payload:
        return None
    return _require_string(parent_name, payload, key)


def _require_string(
    parent_name: str,
    payload: Mapping[str, object],
    key: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CanonicalNotificationJsonError(f"{parent_name}.{key} must be a string")
    return value


def _require_object(field_name: str, value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise CanonicalNotificationJsonError(f"{field_name} must be a JSON object")
    mapping = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in mapping):
        raise CanonicalNotificationJsonError(
            f"{field_name} must contain only string keys"
        )
    return cast(dict[str, object], mapping)


def _reject_unknown_fields(
    field_name: str,
    payload: Mapping[str, object],
    allowed_fields: set[str],
) -> None:
    unknown_fields = sorted(payload.keys() - allowed_fields)
    if unknown_fields:
        unknown = ", ".join(unknown_fields)
        raise CanonicalNotificationJsonError(
            f"{field_name} contains unsupported fields: {unknown}"
        )
