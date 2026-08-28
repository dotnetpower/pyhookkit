"""Canonical notification invariant tests."""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime

import pytest

from pyhookkit.domain.notification import (
    CanonicalNotification,
    Fact,
    Image,
    Link,
    Mention,
    MentionKind,
    Severity,
)


def _notification(
    *,
    schema_version: str = "1.0",
    event_id: str = "example-event-001",
    route: str = "hello-world",
    body: str = "Hello, world!",
    severity: Severity = Severity.INFO,
    title: str | None = None,
    thread_key: str | None = None,
    source_timestamp: datetime | None = None,
    metadata: Mapping[str, str] | None = None,
) -> CanonicalNotification:
    return CanonicalNotification(
        schema_version=schema_version,
        event_id=event_id,
        route=route,
        body=body,
        severity=severity,
        title=title,
        thread_key=thread_key,
        source_timestamp=source_timestamp,
        metadata={} if metadata is None else metadata,
    )


def test_notification_accepts_provider_neutral_values() -> None:
    timestamp = datetime(2026, 8, 28, tzinfo=UTC)
    notification = CanonicalNotification(
        schema_version="1.0",
        event_id="example-event-001",
        route="hello-world",
        body="Hello, world!",
        severity=Severity.INFO,
        title="Greeting",
        facts=(Fact("Environment", "Example"),),
        links=(Link("Details", "https://example.com/details"),),
        mentions=(Mention(MentionKind.USER, "example-owner"),),
        image=Image("https://images.example.com/status.png", "Example status"),
        thread_key="example-thread-001",
        source_timestamp=timestamp,
        metadata={"source": "synthetic", "correlationId": "example-001"},
    )

    assert notification.source_timestamp == timestamp
    assert notification.metadata["source"] == "synthetic"


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: _notification(schema_version="2.0"), "schema version"),
        (lambda: _notification(event_id="not valid"), "event ID"),
        (lambda: _notification(route="Not-Valid"), "route"),
        (lambda: _notification(body="  "), "body"),
        (lambda: _notification(title="  "), "title"),
        (lambda: _notification(thread_key="not valid"), "thread key"),
        (
            lambda: _notification(source_timestamp=datetime(2026, 8, 28)),
            "source timestamp",
        ),
        (
            lambda: _notification(metadata={"unknown": "value"}),
            "unsupported metadata",
        ),
    ],
)
def test_notification_rejects_invalid_values(
    factory: Callable[[], CanonicalNotification],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Fact("", "value"),
        lambda: Fact("key", ""),
        lambda: Link("", "https://example.com"),
    ],
)
def test_value_objects_reject_blank_text(factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        factory()


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "/relative",
    ],
)
def test_link_requires_absolute_https(url: str) -> None:
    with pytest.raises(ValueError, match="absolute HTTPS"):
        Link("Details", url)


@pytest.mark.parametrize(
    ("url", "alt_text", "message"),
    [
        ("http://images.example.com/status.png", "Status", "absolute HTTPS"),
        ("https://images.example.com/status.png", "", "must not be blank"),
    ],
)
def test_image_requires_https_and_alt_text(
    url: str,
    alt_text: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        Image(url, alt_text)


def test_mention_requires_kebab_case_alias() -> None:
    with pytest.raises(ValueError, match="kebab-case"):
        Mention(MentionKind.USER, "Example Owner")


def test_metadata_is_read_only() -> None:
    metadata = {"source": "synthetic"}
    notification = _notification(metadata=metadata)
    metadata["source"] = "changed"

    assert notification.metadata["source"] == "synthetic"


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: _notification(event_id="a" * 129), "event ID"),
        (lambda: _notification(route="a" * 65), "route"),
        (lambda: _notification(title="a" * 151), "title"),
        (lambda: _notification(body="a" * 8001), "body"),
        (lambda: _notification(thread_key="a" * 129), "thread key"),
        (lambda: Fact("a" * 101, "value"), "fact key"),
        (lambda: Fact("key", "a" * 1001), "fact value"),
        (
            lambda: Link("a" * 76, "https://example.com"),
            "link label",
        ),
        (
            lambda: Link("Details", f"https://example.com/{'a' * 2030}"),
            "link URL",
        ),
        (
            lambda: Image(f"https://example.com/{'a' * 2030}", "Example"),
            "image URL",
        ),
        (
            lambda: Image("https://example.com/image.png", "a" * 201),
            "image alt text",
        ),
        (
            lambda: Mention(MentionKind.USER, "a" * 101),
            "mention alias",
        ),
        (
            lambda: _notification(metadata={"source": "a" * 65}),
            "metadata source",
        ),
        (
            lambda: _notification(metadata={"correlationId": "a" * 129}),
            "metadata correlationId",
        ),
    ],
)
def test_value_lengths_match_contract(
    factory: Callable[[], object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: CanonicalNotification(
                schema_version="1.0",
                event_id="example-event-001",
                route="hello-world",
                body="Hello, world!",
                severity=Severity.INFO,
                facts=tuple(Fact(str(index), "value") for index in range(51)),
            ),
            "facts",
        ),
        (
            lambda: CanonicalNotification(
                schema_version="1.0",
                event_id="example-event-001",
                route="hello-world",
                body="Hello, world!",
                severity=Severity.INFO,
                links=tuple(
                    Link(str(index), "https://example.com") for index in range(11)
                ),
            ),
            "links",
        ),
        (
            lambda: CanonicalNotification(
                schema_version="1.0",
                event_id="example-event-001",
                route="hello-world",
                body="Hello, world!",
                severity=Severity.INFO,
                mentions=tuple(
                    Mention(MentionKind.USER, f"user-{index}") for index in range(21)
                ),
            ),
            "mentions",
        ),
    ],
)
def test_collection_sizes_match_contract(
    factory: Callable[[], CanonicalNotification],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        factory()
