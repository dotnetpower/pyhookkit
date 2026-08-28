"""Canonical input for the rich card example."""

from datetime import UTC, datetime

from pyhookkit.domain.notification import (
    CanonicalNotification,
    Fact,
    Severity,
)


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-rich-card-001",
        route="rich-card",
        title="Deployment completed",
        body="The synthetic deployment completed successfully.",
        severity=Severity.SUCCESS,
        facts=(
            Fact("Application", "example-api"),
            Fact("Environment", "staging"),
            Fact("Revision", "abc1234"),
        ),
        source_timestamp=datetime(2026, 8, 28, 2, 5, tzinfo=UTC),
        metadata={"source": "synthetic-deployer"},
    )
