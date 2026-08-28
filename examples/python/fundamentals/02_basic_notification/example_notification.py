"""Canonical input for the basic notification example."""

from datetime import UTC, datetime

from pyhookkit.domain.notification import CanonicalNotification, Severity


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-basic-001",
        route="basic-notification",
        title="Service status",
        body="The example service is operating normally.",
        severity=Severity.SUCCESS,
        source_timestamp=datetime(2026, 8, 28, 2, tzinfo=UTC),
    )
