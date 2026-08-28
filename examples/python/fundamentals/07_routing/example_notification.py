"""Canonical input for the routing example."""

from pyhookkit.domain.notification import CanonicalNotification, Severity


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-routing-001",
        route="platform-alerts",
        title="Routed notification",
        body="This notification uses a logical destination.",
        severity=Severity.INFO,
    )
