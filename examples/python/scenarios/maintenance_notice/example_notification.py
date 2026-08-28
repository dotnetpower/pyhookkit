"""Shared canonical input for the maintenance notice pair."""

from datetime import UTC, datetime

from pyhookkit.domain.notification import (
    CanonicalNotification,
    Fact,
    Link,
    Mention,
    MentionKind,
    Severity,
)


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="scenario-maintenance-notice-001",
        route="service-announcements",
        title="Scheduled maintenance notice",
        body=(
            "INFO: Scheduled maintenance notice. Maintenance affects example-api "
            "and example-worker from 2026-08-30T01:00:00Z to "
            "2026-08-30T02:00:00Z. Expected impact: Brief request retries. "
            "Owner: example-operations. Status page: "
            "https://status.example.com/notices/maintenance-118"
        ),
        severity=Severity.INFO,
        facts=(
            Fact(
                "Window",
                "2026-08-30T01:00:00Z - 2026-08-30T02:00:00Z",
            ),
            Fact("Affected services", "example-api, example-worker"),
            Fact("Expected impact", "Brief request retries"),
        ),
        links=(
            Link(
                "Open status page",
                "https://status.example.com/notices/maintenance-118",
            ),
        ),
        mentions=(Mention(MentionKind.GROUP, "example-operations"),),
        source_timestamp=datetime(2026, 8, 28, 6, tzinfo=UTC),
        metadata={
            "source": "synthetic-maintenance-service",
            "correlationId": "maintenance-118",
        },
    )
