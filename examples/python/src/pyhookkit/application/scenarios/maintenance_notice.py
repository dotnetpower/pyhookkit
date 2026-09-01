"""Reusable maintenance notice scenario construction."""

from collections.abc import Sequence
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

_DEFAULT_ROUTE = "service-announcements"
_DEFAULT_SOURCE = "synthetic-maintenance-service"


@dataclass(frozen=True, slots=True)
class MaintenanceNoticeEvent:
    """Immutable maintenance notice input."""

    event_id: str
    window_start: datetime
    window_end: datetime
    announced_at: datetime
    affected_services: tuple[str, ...]
    expected_impact: str
    owner_alias: str
    status_page_url: str
    correlation_id: str
    route: str = _DEFAULT_ROUTE
    source: str = _DEFAULT_SOURCE

    def __post_init__(self) -> None:
        if not self.affected_services:
            raise ValueError("affected services must contain at least one service")
        for service in self.affected_services:
            validate_fact_value("affected service", "Affected service", service)
        validate_fact_value("expected impact", "Expected impact", self.expected_impact)
        validate_mention_alias(
            "owner alias",
            kind=MentionKind.GROUP,
            alias=self.owner_alias,
        )
        validate_link("status page URL", "Open status page", self.status_page_url)
        validate_notification_envelope(
            event_id=self.event_id,
            route=self.route,
            title="Scheduled maintenance notice",
            body=_body(self),
            severity=Severity.INFO,
            source_timestamp=self.announced_at,
            source=self.source,
            correlation_id=self.correlation_id,
        )


def build_notification(event: MaintenanceNoticeEvent) -> CanonicalNotification:
    """Build one canonical maintenance notice notification."""
    return CanonicalNotification(
        schema_version="1.0",
        event_id=event.event_id,
        route=event.route,
        title="Scheduled maintenance notice",
        body=_body(event),
        severity=Severity.INFO,
        facts=(
            Fact(
                "Window",
                (
                    f"{render_timestamp_text(event.window_start)} - "
                    f"{render_timestamp_text(event.window_end)}"
                ),
            ),
            Fact("Affected services", ", ".join(event.affected_services)),
            Fact("Expected impact", event.expected_impact),
        ),
        links=(Link("Open status page", event.status_page_url),),
        mentions=(Mention(MentionKind.GROUP, event.owner_alias),),
        source_timestamp=event.announced_at,
        metadata={
            "source": event.source,
            "correlationId": event.correlation_id,
        },
    )


def example_event() -> MaintenanceNoticeEvent:
    """Return the committed maintenance notice sample input."""
    return MaintenanceNoticeEvent(
        event_id="scenario-maintenance-notice-001",
        window_start=datetime(2026, 8, 30, 1, tzinfo=UTC),
        window_end=datetime(2026, 8, 30, 2, tzinfo=UTC),
        announced_at=datetime(2026, 8, 28, 6, tzinfo=UTC),
        affected_services=("example-api", "example-worker"),
        expected_impact="Brief request retries",
        owner_alias="example-operations",
        status_page_url="https://status.example.com/notices/maintenance-118",
        correlation_id="maintenance-118",
    )


def build_example_notification() -> CanonicalNotification:
    """Build the committed maintenance notice notification."""
    return build_notification(example_event())


def _body(event: MaintenanceNoticeEvent) -> str:
    return (
        "INFO: Scheduled maintenance notice. Maintenance affects "
        f"{_humanize_services(event.affected_services)} from "
        f"{render_timestamp_text(event.window_start)} to "
        f"{render_timestamp_text(event.window_end)}. "
        f"Expected impact: {event.expected_impact}. "
        f"Owner: {event.owner_alias}. "
        f"Status page: {event.status_page_url}"
    )


def _humanize_services(services: Sequence[str]) -> str:
    if len(services) == 1:
        return services[0]
    if len(services) == 2:
        return f"{services[0]} and {services[1]}"
    return f"{', '.join(services[:-1])}, and {services[-1]}"
