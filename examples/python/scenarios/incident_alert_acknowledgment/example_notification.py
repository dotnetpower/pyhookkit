"""Shared canonical input for the incident alert and acknowledgment pair."""

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
        event_id="scenario-incident-alert-001",
        route="incident-response",
        title="Incident alert: elevated latency",
        body=(
            "ERROR: Incident alert: elevated latency. Incident INC-204 affects "
            "example-checkout since 2026-08-28T04:20:00Z. Status: "
            "unacknowledged. Responder: example-responders. Acknowledge incident: "
            "https://incidents.example.com/incidents/inc-204/acknowledge "
            "Open runbook: "
            "https://runbooks.example.com/services/example-checkout/latency"
        ),
        severity=Severity.ERROR,
        facts=(
            Fact("Incident", "INC-204"),
            Fact("Service", "example-checkout"),
            Fact("Started", "2026-08-28T04:20:00Z"),
            Fact("Status", "Unacknowledged"),
        ),
        links=(
            Link(
                "Acknowledge incident",
                "https://incidents.example.com/incidents/inc-204/acknowledge",
            ),
            Link(
                "Open runbook",
                "https://runbooks.example.com/services/example-checkout/latency",
            ),
        ),
        mentions=(Mention(MentionKind.GROUP, "example-responders"),),
        thread_key="scenario-incident-inc-204",
        source_timestamp=datetime(2026, 8, 28, 4, 20, tzinfo=UTC),
        metadata={
            "source": "synthetic-incident-service",
            "correlationId": "incident-inc-204",
        },
    )
