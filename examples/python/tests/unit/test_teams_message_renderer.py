"""Rich Microsoft Teams Adaptive Card renderer tests."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pyhookkit.adapters.outbound.teams.identity import (
    TeamsIdentity,
    TeamsIdentityDirectory,
    TeamsIdentityNotFoundError,
)
from pyhookkit.adapters.outbound.teams.message_renderer import (
    TeamsActionPresentation,
    TeamsGroupMentionPolicy,
    TeamsHeroImageUrlError,
    TeamsMessageRenderer,
)
from pyhookkit.domain.notification import (
    CanonicalNotification,
    Fact,
    Image,
    Link,
    Mention,
    MentionKind,
    Severity,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_PYTHON_ROOT = _REPOSITORY_ROOT / "examples" / "python"


def _notification(
    *,
    mention_kind: MentionKind | None = None,
) -> CanonicalNotification:
    mentions = () if mention_kind is None else (Mention(mention_kind, "example-owner"),)
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-teams-rich-001",
        route="platform-alerts",
        title="Synthetic service alert",
        body="The synthetic service needs attention.",
        severity=Severity.ERROR,
        facts=(Fact("Service", "example-api"),),
        links=(Link("Open runbook", "https://runbooks.example.com/example-api"),),
        mentions=mentions,
        image=Image(
            "https://images.example.com/example-api.png",
            "Synthetic service diagram",
        ),
        metadata={"source": "synthetic-monitor"},
    )


def test_rich_card_preserves_structured_content() -> None:
    payload = TeamsMessageRenderer().render(_notification())
    serialized = json.dumps(payload, ensure_ascii=False)

    assert '"ColumnSet"' in serialized
    assert '"Action.OpenUrl"' in serialized
    assert '"Image"' in serialized
    assert "CRITICAL" in serialized
    assert "PyHookKit" in serialized
    assert "Synthetic service alert" in serialized
    assert "synthetic-monitor" in serialized
    assert '"speak"' in serialized
    assert '"backgroundImage"' in serialized
    assert (
        "https://assets.pyhookkit.example/samples/editorial/assets/editorialHero.png"
    ) in serialized
    assert '"style": "emphasis"' not in serialized
    assert "🚨" not in serialized
    assert "↗" not in serialized
    assert (
        "Synthetic service alert: The synthetic service needs attention." in serialized
    )
    assert (
        '"style": "accent", "bleed": true, "spacing": "None", "items": '
        '[{"type": "TextBlock", "text": "PYHOOKKIT NOTIFICATION"' in serialized
    )
    assert (
        '"text": "PYHOOKKIT NOTIFICATION", "wrap": true, "weight": "Bolder", '
        '"horizontalAlignment": "Center", "spacing": "None"' in serialized
    )


def test_user_mention_creates_text_and_entity() -> None:
    directory = TeamsIdentityDirectory(
        {
            "example-owner": TeamsIdentity(
                "example-owner@pyhookkit.example",
                "Example Owner",
            )
        }
    )

    payload = TeamsMessageRenderer(directory).render(
        _notification(mention_kind=MentionKind.USER)
    )
    serialized = json.dumps(payload, ensure_ascii=False)

    assert "<at>Example Owner</at>" in serialized
    assert "example-owner@pyhookkit.example" in serialized
    assert '"mention"' in serialized


def test_group_mention_is_explicitly_degraded() -> None:
    payload = TeamsMessageRenderer().render(
        _notification(mention_kind=MentionKind.GROUP)
    )

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "additional Graph member-expansion configuration required" in serialized
    assert "👥" not in serialized


def test_group_mention_can_be_explicitly_omitted() -> None:
    payload = TeamsMessageRenderer(
        group_mention_policy=TeamsGroupMentionPolicy.OMIT
    ).render(_notification(mention_kind=MentionKind.GROUP))

    serialized = json.dumps(payload)
    assert "example-owner" not in serialized
    assert "member-expansion" not in serialized


def test_missing_user_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="identity directory"):
        TeamsMessageRenderer().render(_notification(mention_kind=MentionKind.USER))

    with pytest.raises(TeamsIdentityNotFoundError):
        TeamsMessageRenderer(TeamsIdentityDirectory({})).render(
            _notification(mention_kind=MentionKind.USER)
        )


def test_renderer_rejects_insecure_hero_image() -> None:
    with pytest.raises(TeamsHeroImageUrlError, match="absolute HTTPS"):
        TeamsMessageRenderer(hero_image_url="http://assets.example.com/hero.png")


def test_renderer_can_omit_presentation_hero() -> None:
    payload = TeamsMessageRenderer(hero_image_url=None).render(_notification())

    serialized = json.dumps(payload)
    assert '"backgroundImage"' not in serialized
    assert "PYHOOKKIT NOTIFICATION" not in serialized
    assert "Synthetic service alert" in serialized
    assert "CRITICAL" in serialized


def test_renderer_can_compact_scenario_body_and_hero() -> None:
    payload = TeamsMessageRenderer(
        show_body_in_card=False,
        show_hero_label=False,
        hero_min_height=136,
    ).render(_notification())

    serialized = json.dumps(payload)
    assert '"minHeight": "136px"' in serialized
    assert "PYHOOKKIT NOTIFICATION" not in serialized
    assert (
        '"fallbackText": "Synthetic service alert: '
        'The synthetic service needs attention."' in serialized
    )
    body_marker = '"body":'
    assert (
        "The synthetic service needs attention."
        not in serialized.split(
            body_marker,
            maxsplit=1,
        )[1]
    )


def test_renderer_rejects_invalid_hero_height() -> None:
    with pytest.raises(ValueError, match="minimum height"):
        TeamsMessageRenderer(hero_min_height=0)


def test_image_without_hero_contains_one_visual() -> None:
    payload = TeamsMessageRenderer(hero_image_url=None).render(_notification())

    serialized = json.dumps(payload)
    assert serialized.count('"type": "Image"') == 1
    assert '"backgroundImage"' not in serialized
    assert "Synthetic service diagram" in serialized


@pytest.mark.parametrize(
    ("identifier", "display_name"),
    [("", "Example Owner"), ("example-owner", "")],
)
def test_identity_rejects_blank_values(
    identifier: str,
    display_name: str,
) -> None:
    with pytest.raises(ValueError):
        TeamsIdentity(identifier, display_name)


@pytest.mark.parametrize(
    ("example_directory", "vector_directory"),
    [
        ("02_basic_notification", "basic-notification"),
        ("03_rich_card", "rich-card"),
        ("04_mention", "mention"),
        ("05_link_and_action", "link-and-action"),
        ("06_image", "image"),
        ("07_routing", "routing"),
        ("08_thread_or_reply", "thread-or-reply"),
        ("09_update_and_delete", "update-and-delete"),
        ("10_error_and_retry", "error-and-retry"),
    ],
)
def test_teams_fundamental_matches_snapshot(
    example_directory: str,
    vector_directory: str,
) -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(_PYTHON_ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "teams.py"],
        cwd=_PYTHON_ROOT / "fundamentals" / example_directory,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    expected_path = (
        _REPOSITORY_ROOT
        / "contracts"
        / "test-vectors"
        / "fundamentals"
        / vector_directory
        / "teams.expected.json"
    )

    assert json.loads(completed.stdout) == json.loads(expected_path.read_text())


def test_basic_notification_preserves_semantics_across_providers() -> None:
    vector_directory = (
        _REPOSITORY_ROOT
        / "contracts"
        / "test-vectors"
        / "fundamentals"
        / "basic-notification"
    )
    slack_payload = (vector_directory / "slack.expected.json").read_text()
    teams_payload = (vector_directory / "teams.expected.json").read_text()

    for value in (
        "Service status",
        "The example service is operating normally.",
        "2026-08-28T02:00:00+00:00",
    ):
        assert value in slack_payload
        assert value in teams_payload
    assert "#2EB67D" in slack_payload
    assert '"text": "SUCCESS"' in teams_payload
    assert '"color": "Good"' in teams_payload


def test_rich_card_uses_same_presentation_hero_across_providers() -> None:
    vector_directory = (
        _REPOSITORY_ROOT / "contracts" / "test-vectors" / "fundamentals" / "rich-card"
    )
    hero_url = "https://assets.pyhookkit.example/samples/cafe-menu/assets/hero.png"

    assert hero_url in (vector_directory / "slack.expected.json").read_text()
    assert hero_url in (vector_directory / "teams.expected.json").read_text()


def test_capability_notice_is_visible_and_preserves_thread_key() -> None:
    notification = CanonicalNotification(
        schema_version="1.0",
        event_id="example-capability-001",
        route="platform-alerts",
        body="Synthetic follow-up completed.",
        severity=Severity.SUCCESS,
        thread_key="example-parent-001",
    )

    payload = TeamsMessageRenderer(
        hero_image_url=None,
        capability_notice="True replies require an advanced adapter.",
    ).render(notification)
    serialized = json.dumps(payload)

    assert "TEAMS WORKFLOW CAPABILITY" in serialized
    assert "True replies require an advanced adapter." in serialized
    assert "example-parent-001" in serialized
    assert (
        "Teams Workflow capability: True replies require an advanced adapter."
        in serialized
    )


def test_capability_notice_rejects_blank_text() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        TeamsMessageRenderer(capability_notice=" ")


def test_edge_to_edge_action_panel_preserves_link() -> None:
    payload = TeamsMessageRenderer(
        hero_image_url=None,
        action_presentation=TeamsActionPresentation.EDGE_TO_EDGE,
    ).render(_notification())

    serialized = json.dumps(payload)
    assert '"style": "accent"' in serialized
    assert '"bleed": true' in serialized
    assert '"type": "ActionSet"' in serialized
    assert '"type": "Action.OpenUrl"' in serialized
    assert "https://runbooks.example.com/example-api" in serialized
    assert "Continue to the investigation details" in serialized
    assert "NEXT STEP" not in serialized
    assert '"actions": [' not in serialized.split('"body":', maxsplit=1)[0]
