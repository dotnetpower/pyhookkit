"""Canonical input for the retry example."""

from pyhookkit.domain.notification import CanonicalNotification, Severity


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-retry-001",
        route="platform-alerts",
        body="Synthetic retry verification.",
        severity=Severity.INFO,
    )
