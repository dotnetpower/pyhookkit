"""Canonical input for the link and action example."""

from pyhookkit.domain.notification import (
    CanonicalNotification,
    Link,
    Severity,
)


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-action-001",
        route="platform-alerts",
        title="Investigation available",
        body="Open the synthetic investigation details.",
        severity=Severity.INFO,
        links=(
            Link(
                "View details",
                "https://example.com/notifications/example-001",
            ),
        ),
    )
