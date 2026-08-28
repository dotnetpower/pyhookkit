"""Canonical input for the thread reply example."""

from pyhookkit.domain.notification import CanonicalNotification, Severity


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-reply-001",
        route="platform-alerts",
        body="Synthetic follow-up completed.",
        severity=Severity.SUCCESS,
        thread_key="example-deployment-001",
    )
