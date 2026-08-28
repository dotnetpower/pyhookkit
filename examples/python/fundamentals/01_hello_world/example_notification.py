"""Shared canonical input for the Hello World pair."""

from pyhookkit.domain.notification import CanonicalNotification, Severity


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-hello-world-001",
        route="hello-world",
        body="Hello, world!",
        severity=Severity.INFO,
    )
