"""Reusable deployment result scenario construction."""

from dataclasses import dataclass
from datetime import UTC, datetime

from pyhookkit.application.scenarios.validation import (
    render_timestamp_text,
    validate_fact_value,
    validate_link,
    validate_notification_envelope,
)
from pyhookkit.domain.notification import CanonicalNotification, Fact, Link, Severity

_DEFAULT_ROUTE = "release-notifications"
_DEFAULT_SOURCE = "synthetic-release-service"


@dataclass(frozen=True, slots=True)
class DeploymentResultEvent:
    """Immutable deployment result input."""

    event_id: str
    service: str
    deployment_environment: str
    revision: str
    duration: str
    completed_at: datetime
    deployment_url: str
    correlation_id: str
    route: str = _DEFAULT_ROUTE
    source: str = _DEFAULT_SOURCE

    def __post_init__(self) -> None:
        validate_fact_value("service", "Service", self.service)
        validate_fact_value(
            "deployment environment",
            "Environment",
            self.deployment_environment,
        )
        validate_fact_value("revision", "Revision", self.revision)
        validate_fact_value("duration", "Duration", self.duration)
        validate_link("deployment URL", "View deployment", self.deployment_url)
        validate_notification_envelope(
            event_id=self.event_id,
            route=self.route,
            title="Deployment succeeded",
            body=_body(self),
            severity=Severity.SUCCESS,
            source_timestamp=self.completed_at,
            source=self.source,
            correlation_id=self.correlation_id,
        )


def build_notification(event: DeploymentResultEvent) -> CanonicalNotification:
    """Build one canonical deployment result notification."""
    return CanonicalNotification(
        schema_version="1.0",
        event_id=event.event_id,
        route=event.route,
        title="Deployment succeeded",
        body=_body(event),
        severity=Severity.SUCCESS,
        facts=(
            Fact("Service", event.service),
            Fact("Environment", event.deployment_environment),
            Fact("Revision", event.revision),
            Fact("Duration", event.duration),
        ),
        links=(Link("View deployment", event.deployment_url),),
        source_timestamp=event.completed_at,
        metadata={
            "source": event.source,
            "correlationId": event.correlation_id,
        },
    )


def example_event() -> DeploymentResultEvent:
    """Return the committed deployment result sample input."""
    return DeploymentResultEvent(
        event_id="scenario-deployment-result-001",
        service="example-api",
        deployment_environment="staging",
        revision="9f3a2c1",
        duration="2m 18s",
        completed_at=datetime(2026, 8, 28, 3, 15, tzinfo=UTC),
        deployment_url="https://deployments.example.com/runs/run-1042",
        correlation_id="deploy-run-1042",
    )


def build_example_notification() -> CanonicalNotification:
    """Build the committed deployment result notification."""
    return build_notification(example_event())


def _body(event: DeploymentResultEvent) -> str:
    completed_at = render_timestamp_text(event.completed_at)
    return (
        "SUCCESS: Deployment succeeded. "
        f"{event.service} revision {event.revision} deployed to "
        f"{event.deployment_environment} in {event.duration} at {completed_at}. "
        f"View deployment: {event.deployment_url}"
    )
