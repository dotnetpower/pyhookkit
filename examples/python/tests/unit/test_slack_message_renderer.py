"""Progressive Slack renderer tests."""

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyhookkit.adapters.outbound.slack.identity import (
    SlackIdentity,
    SlackIdentityDirectory,
    SlackIdentityNotFoundError,
)
from pyhookkit.adapters.outbound.slack.message_reference import (
    SlackMessageReference,
)
from pyhookkit.adapters.outbound.slack.message_renderer import (
    SlackHeroImageUrlError,
    SlackMessageRenderer,
    SlackPayloadLimitError,
)
from pyhookkit.adapters.outbound.slack.mutation_renderer import (
    SlackMutationRenderer,
)
from pyhookkit.adapters.outbound.slack.thread_renderer import (
    SlackThreadRenderer,
)
from pyhookkit.domain.notification import (
    CanonicalNotification,
    Fact,
    Image,
    Link,
    Mention,
    MentionKind,
    MetadataValue,
    Severity,
)
from pyhookkit.entrypoints.example_asset import example_asset_marker
from pyhookkit.json_types import JsonObject, JsonValue

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_VECTORS = _REPOSITORY_ROOT / "contracts" / "test-vectors" / "fundamentals"


def _load_expected(capability: str, filename: str = "slack.expected.json") -> object:
    with (_VECTORS / capability / filename).open(encoding="utf-8") as file:
        return json.load(file)


def _base_notification(
    *,
    event_id: str = "example-test-001",
    route: str = "platform-alerts",
    title: str | None = None,
    body: str = "Example body.",
    severity: Severity = Severity.INFO,
    facts: tuple[Fact, ...] = (),
    links: tuple[Link, ...] = (),
    mentions: tuple[Mention, ...] = (),
    image: Image | None = None,
    thread_key: str | None = None,
    source_timestamp: datetime | None = None,
    metadata: Mapping[str, MetadataValue] | None = None,
) -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id=event_id,
        route=route,
        title=title,
        body=body,
        severity=severity,
        facts=facts,
        links=links,
        mentions=mentions,
        image=image,
        thread_key=thread_key,
        source_timestamp=source_timestamp,
        metadata={} if metadata is None else metadata,
    )


def _basic_notification() -> CanonicalNotification:
    return _base_notification(
        event_id="example-basic-001",
        route="basic-notification",
        title="Service status",
        body="The example service is operating normally.",
        severity=Severity.SUCCESS,
        source_timestamp=datetime(2026, 8, 28, 2, tzinfo=UTC),
    )


def _rich_notification() -> CanonicalNotification:
    return _base_notification(
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


def _mention_notification() -> CanonicalNotification:
    return _base_notification(
        event_id="example-mention-001",
        title="Action required",
        body="Review the synthetic alert.",
        severity=Severity.WARNING,
        mentions=(
            Mention(MentionKind.USER, "example-owner"),
            Mention(MentionKind.GROUP, "example-responders"),
        ),
    )


def _identity_directory() -> SlackIdentityDirectory:
    return SlackIdentityDirectory(
        {
            "example-owner": SlackIdentity(MentionKind.USER, "U00000001"),
            "example-responders": SlackIdentity(MentionKind.GROUP, "S00000001"),
        }
    )


@pytest.mark.parametrize(
    ("capability", "notification_factory"),
    [
        ("basic-notification", _basic_notification),
        ("rich-card", _rich_notification),
        (
            "link-and-action",
            lambda: _base_notification(
                event_id="example-action-001",
                title="Investigation available",
                body="Open the synthetic investigation details.",
                links=(
                    Link(
                        "View details",
                        "https://example.com/notifications/example-001",
                    ),
                ),
            ),
        ),
        (
            "image",
            lambda: _base_notification(
                event_id="example-image-001",
                title="Sample image",
                body="A publicly hosted sample image is attached.",
                image=Image(
                    "https://assets.pyhookkit.example/samples/recipe/assets/"
                    "recipe_image.png",
                    "Glazed chicken with broccoli from the Microsoft Adaptive "
                    "Cards recipe sample",
                ),
            ),
        ),
        (
            "routing",
            lambda: _base_notification(
                event_id="example-routing-001",
                title="Routed notification",
                body="This notification uses a logical destination.",
            ),
        ),
    ],
)
def test_slack_capability_matches_snapshot(
    capability: str,
    notification_factory: Callable[[], CanonicalNotification],
) -> None:
    hero_image_url = (
        example_asset_marker("samples/cafe-menu/assets/hero.png")
        if capability == "rich-card"
        else None
    )
    payload = SlackMessageRenderer(hero_image_url=hero_image_url).render(
        notification_factory()
    )

    assert payload == _load_expected(capability)


def test_renderer_rejects_insecure_hero_image() -> None:
    with pytest.raises(SlackHeroImageUrlError, match="absolute HTTPS"):
        SlackMessageRenderer(hero_image_url="http://assets.example.com/hero.png")


def test_slack_mentions_match_snapshot() -> None:
    payload = SlackMessageRenderer(_identity_directory()).render(
        _mention_notification()
    )

    assert payload == _load_expected("mention")


def test_slack_renderer_requires_identity_directory() -> None:
    with pytest.raises(ValueError, match="identity directory"):
        SlackMessageRenderer().render(_mention_notification())


def test_slack_identity_directory_rejects_missing_or_wrong_kind() -> None:
    missing = SlackIdentityDirectory({})
    wrong_kind = SlackIdentityDirectory(
        {"example-owner": SlackIdentity(MentionKind.GROUP, "S00000001")}
    )
    mention = Mention(MentionKind.USER, "example-owner")

    with pytest.raises(SlackIdentityNotFoundError, match="not configured"):
        missing.render(mention)
    with pytest.raises(SlackIdentityNotFoundError, match="does not match"):
        wrong_kind.render(mention)


@pytest.mark.parametrize(
    ("kind", "identifier"),
    [
        (MentionKind.USER, "S00000001"),
        (MentionKind.GROUP, "U00000001"),
    ],
)
def test_slack_identity_validates_provider_identifier(
    kind: MentionKind,
    identifier: str,
) -> None:
    with pytest.raises(ValueError, match="invalid Slack"):
        SlackIdentity(kind, identifier)


def test_slack_renderer_escapes_mrkdwn_and_chunks_limits() -> None:
    notification = _base_notification(
        body="<unsafe & text>" * 300,
        facts=tuple(Fact(f"Key {index}", "Value") for index in range(11)),
    )

    payload = SlackMessageRenderer().render(notification)
    attachment = _first_attachment(payload)
    blocks = attachment["blocks"]

    assert isinstance(blocks, list)
    assert len(blocks) == 5
    assert "&lt;unsafe &amp; text&gt;" in str(blocks[0])


def test_slack_renderer_rejects_expanded_fact_over_limit() -> None:
    notification = _base_notification(facts=(Fact("Key", "<" * 1000),))

    with pytest.raises(SlackPayloadLimitError, match="2000"):
        SlackMessageRenderer().render(notification)


def test_slack_body_chunks_do_not_split_escaped_entities() -> None:
    notification = _base_notification(body=("x" * 2998) + "&" + ("y" * 10))

    attachment = _first_attachment(SlackMessageRenderer().render(notification))
    blocks = attachment["blocks"]
    assert isinstance(blocks, list)
    first_text = _section_text(blocks[0])
    second_text = _section_text(blocks[1])

    assert first_text == "x" * 2998
    assert second_text == "&amp;" + ("y" * 10)
    assert len(first_text) <= 3000
    assert len(second_text) <= 3000


def test_thread_reply_matches_snapshot() -> None:
    notification = _base_notification(
        event_id="example-reply-001",
        body="Synthetic follow-up completed.",
        severity=Severity.SUCCESS,
        thread_key="example-deployment-001",
    )
    parent = SlackMessageReference("C00000001", "1724811000.000001")

    payload = SlackThreadRenderer(SlackMessageRenderer()).render(
        notification,
        parent,
    )

    assert payload == _load_expected("thread-or-reply")


def test_mutation_payloads_match_snapshots() -> None:
    notification = _base_notification(
        event_id="example-mutation-001",
        title="Status corrected",
        body="The synthetic status has been corrected.",
        severity=Severity.SUCCESS,
    )
    reference = SlackMessageReference("C00000001", "1724811000.000001")
    renderer = SlackMutationRenderer(SlackMessageRenderer())

    assert renderer.render_update(reference, notification) == _load_expected(
        "update-and-delete",
        "slack.update.expected.json",
    )
    assert renderer.render_delete(reference) == _load_expected(
        "update-and-delete",
        "slack.delete.expected.json",
    )


@pytest.mark.parametrize(
    ("channel_id", "message_ts", "message"),
    [
        ("not-a-channel", "1724811000.000001", "channel"),
        ("C00000001", "not-a-timestamp", "timestamp"),
    ],
)
def test_slack_message_reference_validates_coordinates(
    channel_id: str,
    message_ts: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        SlackMessageReference(channel_id, message_ts)


def _first_attachment(payload: JsonObject) -> JsonObject:
    attachments = payload["attachments"]
    assert isinstance(attachments, list)
    attachment = attachments[0]
    assert isinstance(attachment, dict)
    return attachment


def _section_text(value: JsonValue) -> str:
    assert isinstance(value, dict)
    text_object = value["text"]
    assert isinstance(text_object, dict)
    text = text_object["text"]
    assert isinstance(text, str)
    return text
