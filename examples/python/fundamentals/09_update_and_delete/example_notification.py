"""Canonical replacement content for the mutation example."""

from pyhookkit.domain.notification import CanonicalNotification, Severity


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-mutation-001",
        route="platform-alerts",
        title="Status corrected",
        body="The synthetic status has been corrected.",
        severity=Severity.SUCCESS,
    )
