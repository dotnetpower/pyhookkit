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
    assert "group notification unavailable" in serialized
    assert "👥" not in serialized


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
        ("03_rich_card", "rich-card"),
        ("06_image", "image"),
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
