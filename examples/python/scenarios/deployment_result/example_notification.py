"""Shared canonical input for the deployment result pair."""

from datetime import UTC, datetime

from pyhookkit.domain.notification import CanonicalNotification, Fact, Link, Severity


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="scenario-deployment-result-001",
        route="release-notifications",
        title="Deployment succeeded",
        body=(
            "SUCCESS: Deployment succeeded. example-api revision 9f3a2c1 deployed "
            "to staging in 2m 18s at 2026-08-28T03:15:00Z. View deployment: "
            "https://deployments.example.com/runs/run-1042"
        ),
        severity=Severity.SUCCESS,
        facts=(
            Fact("Service", "example-api"),
            Fact("Environment", "staging"),
            Fact("Revision", "9f3a2c1"),
            Fact("Duration", "2m 18s"),
        ),
        links=(
            Link(
                "View deployment",
                "https://deployments.example.com/runs/run-1042",
            ),
        ),
        source_timestamp=datetime(2026, 8, 28, 3, 15, tzinfo=UTC),
        metadata={
            "source": "synthetic-release-service",
            "correlationId": "deploy-run-1042",
        },
    )
