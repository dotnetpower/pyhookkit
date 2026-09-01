"""Scenario input validation through canonical domain values."""

from datetime import datetime

from pyhookkit.domain.notification import (
    CanonicalNotification,
    Fact,
    Link,
    Mention,
    MentionKind,
    Severity,
)


def validate_fact_value(field_name: str, label: str, value: str) -> None:
    """Validate scenario text by reusing canonical fact constraints."""
    try:
        Fact(label, value)
    except ValueError as error:
        raise ValueError(f"{field_name} is invalid: {error}") from error


def validate_link(field_name: str, label: str, url: str) -> None:
    """Validate scenario links by reusing canonical link constraints."""
    try:
        Link(label, url)
    except ValueError as error:
        raise ValueError(f"{field_name} is invalid: {error}") from error


def validate_mention_alias(
    field_name: str,
    *,
    kind: MentionKind,
    alias: str,
) -> None:
    """Validate logical mention aliases by reusing canonical mention rules."""
    try:
        Mention(kind, alias)
    except ValueError as error:
        raise ValueError(f"{field_name} is invalid: {error}") from error


def validate_notification_envelope(
    *,
    event_id: str,
    route: str,
    title: str,
    body: str,
    severity: Severity,
    source_timestamp: datetime,
    source: str,
    correlation_id: str,
    thread_key: str | None = None,
) -> None:
    """Validate shared notification envelope fields via the domain model."""
    CanonicalNotification(
        schema_version="1.0",
        event_id=event_id,
        route=route,
        title=title,
        body=body,
        severity=severity,
        source_timestamp=source_timestamp,
        thread_key=thread_key,
        metadata={
            "source": source,
            "correlationId": correlation_id,
        },
    )


def render_timestamp_text(value: datetime) -> str:
    """Render scenario timestamps with committed UTC shorthand."""
    return value.isoformat().replace("+00:00", "Z")
