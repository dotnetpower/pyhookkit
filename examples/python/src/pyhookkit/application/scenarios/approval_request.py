"""Reusable approval request scenario construction."""

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

_DEFAULT_ROUTE = "change-approvals"
_DEFAULT_SOURCE = "synthetic-change-service"


@dataclass(frozen=True, slots=True)
class ApprovalRequestEvent:
    """Immutable approval request input."""

    event_id: str
    request_id: str
    subject: str
    requester: str
    requested_at: datetime
    deadline_at: datetime
    approver_alias: str
    review_url: str
    correlation_id: str
    route: str = _DEFAULT_ROUTE
    source: str = _DEFAULT_SOURCE

    def __post_init__(self) -> None:
        validate_fact_value("request ID", "Request", self.request_id)
        validate_fact_value("subject", "Subject", self.subject)
        validate_fact_value("requester", "Requester", self.requester)
        validate_mention_alias(
            "approver alias",
            kind=MentionKind.USER,
            alias=self.approver_alias,
        )
        validate_link("review URL", "Review request", self.review_url)
        validate_notification_envelope(
            event_id=self.event_id,
            route=self.route,
            title="Approval requested",
            body=_body(self),
            severity=Severity.WARNING,
            source_timestamp=self.requested_at,
            source=self.source,
            correlation_id=self.correlation_id,
        )


def build_notification(event: ApprovalRequestEvent) -> CanonicalNotification:
    """Build one canonical approval request notification."""
    return CanonicalNotification(
        schema_version="1.0",
        event_id=event.event_id,
        route=event.route,
        title="Approval requested",
        body=_body(event),
        severity=Severity.WARNING,
        facts=(
            Fact("Request", event.request_id),
            Fact("Subject", event.subject),
            Fact("Requester", event.requester),
            Fact("Deadline", render_timestamp_text(event.deadline_at)),
        ),
        links=(Link("Review request", event.review_url),),
        mentions=(Mention(MentionKind.USER, event.approver_alias),),
        source_timestamp=event.requested_at,
        metadata={
            "source": event.source,
            "correlationId": event.correlation_id,
        },
    )


def example_event() -> ApprovalRequestEvent:
    """Return the committed approval request sample input."""
    return ApprovalRequestEvent(
        event_id="scenario-approval-request-001",
        request_id="APR-307",
        subject="example-api 2026.08.28",
        requester="example-requester",
        requested_at=datetime(2026, 8, 28, 5, 10, tzinfo=UTC),
        deadline_at=datetime(2026, 8, 28, 7, tzinfo=UTC),
        approver_alias="example-approver",
        review_url="https://approvals.example.com/requests/apr-307",
        correlation_id="approval-apr-307",
    )


def build_example_notification() -> CanonicalNotification:
    """Build the committed approval request notification."""
    return build_notification(example_event())


def _body(event: ApprovalRequestEvent) -> str:
    deadline_at = render_timestamp_text(event.deadline_at)
    return (
        "WARNING: Approval requested. "
        f"Request {event.request_id} from {event.requester} is for release "
        f"{event.subject} before {deadline_at}. "
        f"Approver: {event.approver_alias}. "
        f"Review request: {event.review_url}"
    )
