"""Canonical input for the mention example."""

from pyhookkit.domain.notification import (
    CanonicalNotification,
    Mention,
    MentionKind,
    Severity,
)


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-mention-001",
        route="platform-alerts",
        title="Action required",
        body="Review the synthetic alert.",
        severity=Severity.WARNING,
        mentions=(
            Mention(MentionKind.USER, "example-owner"),
            Mention(MentionKind.GROUP, "example-responders"),
        ),
    )
