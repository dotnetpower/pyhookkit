"""Reusable incident alert and acknowledgment scenario construction."""

from dataclasses import dataclass
from datetime import UTC, datetime

from pyhookkit.application.scenarios.validation import (
    render_timestamp_text,
    validate_fact_value,
    validate_link,
    validate_mention_alias,
    validate_notification_envelope,
)
from pyhookkit.domain.notification import (
    CanonicalNotification,
    Fact,
    Link,
    Mention,
    MentionKind,
    Severity,
)

_DEFAULT_ROUTE = "incident-response"
_DEFAULT_SOURCE = "synthetic-incident-service"


@dataclass(frozen=True, slots=True)
class IncidentAlertAcknowledgmentEvent:
    """Immutable incident alert input."""

    event_id: str
    incident_id: str
    service: str
    started_at: datetime
    status: str
    responder_alias: str
    acknowledgment_url: str
    runbook_url: str
    correlation_id: str
    route: str = _DEFAULT_ROUTE
    source: str = _DEFAULT_SOURCE
    thread_key: str | None = None

    def __post_init__(self) -> None:
        validate_fact_value("incident ID", "Incident", self.incident_id)
        validate_fact_value("service", "Service", self.service)
        validate_fact_value("status", "Status", self.status)
        validate_mention_alias(
            "responder alias",
            kind=MentionKind.GROUP,
            alias=self.responder_alias,
        )
        validate_link(
            "acknowledgment URL",
            "Acknowledge incident",
            self.acknowledgment_url,
        )
        validate_link("runbook URL", "Open runbook", self.runbook_url)
        validate_notification_envelope(
            event_id=self.event_id,
            route=self.route,
            title="Incident alert: elevated latency",
            body=_body(self),
            severity=Severity.ERROR,
            source_timestamp=self.started_at,
            source=self.source,
            correlation_id=self.correlation_id,
            thread_key=self.resolved_thread_key,
        )

    @property
    def resolved_thread_key(self) -> str:
        """Return the explicit or derived thread key."""
        return self.thread_key or f"scenario-incident-{self.incident_id.lower()}"


def build_notification(
    event: IncidentAlertAcknowledgmentEvent,
) -> CanonicalNotification:
    """Build one canonical incident alert notification."""
    started_at = render_timestamp_text(event.started_at)
    return CanonicalNotification(
        schema_version="1.0",
        event_id=event.event_id,
        route=event.route,
        title="Incident alert: elevated latency",
        body=_body(event),
        severity=Severity.ERROR,
        facts=(
            Fact("Incident", event.incident_id),
            Fact("Service", event.service),
            Fact("Started", started_at),
            Fact("Status", event.status.capitalize()),
        ),
        links=(
            Link("Acknowledge incident", event.acknowledgment_url),
            Link("Open runbook", event.runbook_url),
        ),
        mentions=(Mention(MentionKind.GROUP, event.responder_alias),),
        thread_key=event.resolved_thread_key,
        source_timestamp=event.started_at,
        metadata={
            "source": event.source,
            "correlationId": event.correlation_id,
        },
    )


def example_event() -> IncidentAlertAcknowledgmentEvent:
    """Return the committed incident alert sample input."""
    return IncidentAlertAcknowledgmentEvent(
        event_id="scenario-incident-alert-001",
        incident_id="INC-204",
        service="example-checkout",
        started_at=datetime(2026, 8, 28, 4, 20, tzinfo=UTC),
        status="unacknowledged",
        responder_alias="example-responders",
        acknowledgment_url=(
            "https://incidents.example.com/incidents/inc-204/acknowledge"
        ),
        runbook_url="https://runbooks.example.com/services/example-checkout/latency",
        correlation_id="incident-inc-204",
    )


def build_example_notification() -> CanonicalNotification:
    """Build the committed incident alert notification."""
    return build_notification(example_event())


def _body(event: IncidentAlertAcknowledgmentEvent) -> str:
    started_at = render_timestamp_text(event.started_at)
    return (
        "ERROR: Incident alert: elevated latency. "
        f"Incident {event.incident_id} affects {event.service} since {started_at}. "
        f"Status: {event.status}. Responder: {event.responder_alias}. "
        f"Acknowledge incident: {event.acknowledgment_url} "
        f"Open runbook: {event.runbook_url}"
    )
