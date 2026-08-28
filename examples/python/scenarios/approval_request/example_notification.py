"""Shared canonical input for the approval request pair."""

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
        event_id="scenario-approval-request-001",
        route="change-approvals",
        title="Approval requested",
        body=(
            "WARNING: Approval requested. Request APR-307 from example-requester "
            "is for release example-api 2026.08.28 before "
            "2026-08-28T07:00:00Z. Approver: example-approver. Review request: "
            "https://approvals.example.com/requests/apr-307"
        ),
        severity=Severity.WARNING,
        facts=(
            Fact("Request", "APR-307"),
            Fact("Subject", "example-api 2026.08.28"),
            Fact("Requester", "example-requester"),
            Fact("Deadline", "2026-08-28T07:00:00Z"),
        ),
        links=(
            Link(
                "Review request",
                "https://approvals.example.com/requests/apr-307",
            ),
        ),
        mentions=(Mention(MentionKind.USER, "example-approver"),),
        source_timestamp=datetime(2026, 8, 28, 5, 10, tzinfo=UTC),
        metadata={
            "source": "synthetic-change-service",
            "correlationId": "approval-apr-307",
        },
    )
