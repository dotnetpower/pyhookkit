"""Canonical notification JSON contract serialization tests."""

from datetime import UTC, datetime

from pyhookkit.adapters.outbound.canonical_notification_json import (
    canonical_notification_to_json,
)
from pyhookkit.domain.notification import (
    CanonicalNotification,
    Fact,
    Image,
    Link,
    Mention,
    MentionKind,
    Severity,
)


def test_serializer_uses_contract_names_and_omits_empty_values() -> None:
    notification = CanonicalNotification(
        schema_version="1.0",
        event_id="example-contract-001",
        route="platform-alerts",
        title="Example",
        body="Synthetic notification.",
        severity=Severity.WARNING,
        facts=(Fact("Environment", "staging"),),
        links=(Link("Details", "https://example.com/details"),),
        mentions=(Mention(MentionKind.USER, "example-owner"),),
        image=Image("https://example.com/image.png", "Example image"),
        thread_key="example-thread-001",
        source_timestamp=datetime(2026, 8, 28, tzinfo=UTC),
        metadata={"source": "synthetic"},
    )

    assert canonical_notification_to_json(notification) == {
        "schemaVersion": "1.0",
        "eventId": "example-contract-001",
        "route": "platform-alerts",
        "title": "Example",
        "body": "Synthetic notification.",
        "severity": "warning",
        "facts": [{"key": "Environment", "value": "staging"}],
        "links": [{"label": "Details", "url": "https://example.com/details"}],
        "mentions": [{"kind": "user", "alias": "example-owner"}],
        "image": {
            "url": "https://example.com/image.png",
            "altText": "Example image",
        },
        "threadKey": "example-thread-001",
        "sourceTimestamp": "2026-08-28T00:00:00+00:00",
        "metadata": {"source": "synthetic"},
    }


def test_serializer_omits_absent_optional_fields() -> None:
    notification = CanonicalNotification(
        schema_version="1.0",
        event_id="example-contract-002",
        route="hello-world",
        body="Hello.",
        severity=Severity.INFO,
    )

    assert canonical_notification_to_json(notification) == {
        "schemaVersion": "1.0",
        "eventId": "example-contract-002",
        "route": "hello-world",
        "body": "Hello.",
        "severity": "info",
    }
