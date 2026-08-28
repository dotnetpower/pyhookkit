"""Canonical notification JSON contract serialization."""

from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.json_types import JsonObject, JsonValue


def canonical_notification_to_json(
    notification: CanonicalNotification,
) -> JsonObject:
    """Serialize a domain notification using contract field names."""
    payload: JsonObject = {
        "schemaVersion": notification.schema_version,
        "eventId": notification.event_id,
        "route": notification.route,
        "body": notification.body,
        "severity": notification.severity.value,
    }
    optional_values: tuple[tuple[str, JsonValue | None], ...] = (
        ("title", notification.title),
        (
            "facts",
            [{"key": fact.key, "value": fact.value} for fact in notification.facts]
            or None,
        ),
        (
            "links",
            [{"label": link.label, "url": link.url} for link in notification.links]
            or None,
        ),
        (
            "mentions",
            [
                {"kind": mention.kind.value, "alias": mention.alias}
                for mention in notification.mentions
            ]
            or None,
        ),
        (
            "image",
            (
                {
                    "url": notification.image.url,
                    "altText": notification.image.alt_text,
                }
                if notification.image is not None
                else None
            ),
        ),
        ("threadKey", notification.thread_key),
        (
            "sourceTimestamp",
            (
                notification.source_timestamp.isoformat()
                if notification.source_timestamp is not None
                else None
            ),
        ),
        ("metadata", dict(notification.metadata) or None),
    )
    payload.update(
        (field_name, value)
        for field_name, value in optional_values
        if value is not None
    )
    return payload
