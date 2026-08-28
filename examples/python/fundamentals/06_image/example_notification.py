"""Canonical input for the image example."""

from pyhookkit.domain.notification import (
    CanonicalNotification,
    Image,
    Severity,
)


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-image-001",
        route="platform-alerts",
        title="Service topology",
        body="The synthetic service topology is attached.",
        severity=Severity.INFO,
        image=Image(
            "https://images.example.com/status/example-service.png",
            "Synthetic service topology",
        ),
    )
