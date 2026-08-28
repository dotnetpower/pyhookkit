"""Paired Hello World renderer tests."""

import json
from pathlib import Path

from pyhookkit.adapters.outbound.slack.text_renderer import SlackTextRenderer
from pyhookkit.adapters.outbound.teams.text_renderer import TeamsTextRenderer
from pyhookkit.domain.notification import CanonicalNotification, Severity
from pyhookkit.json_types import JsonObject, JsonValue
from pyhookkit.ports.message_renderer import MessageRenderer

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_VECTOR_DIRECTORY = (
    _REPOSITORY_ROOT / "contracts" / "test-vectors" / "fundamentals" / "hello-world"
)


def _notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-hello-world-001",
        route="hello-world",
        body="Hello, world!",
        severity=Severity.INFO,
    )


def _expected_payload(provider: str) -> object:
    path = _VECTOR_DIRECTORY / f"{provider}.expected.json"
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _render(renderer: MessageRenderer) -> JsonObject:
    return renderer.render(_notification())


def _contains_text(value: JsonValue, expected: str) -> bool:
    if isinstance(value, str):
        return value == expected
    if isinstance(value, list):
        return any(_contains_text(item, expected) for item in value)
    if isinstance(value, dict):
        return any(_contains_text(item, expected) for item in value.values())
    return False


def test_slack_hello_world_matches_snapshot() -> None:
    assert _render(SlackTextRenderer()) == _expected_payload("slack")


def test_teams_hello_world_matches_snapshot() -> None:
    assert _render(TeamsTextRenderer()) == _expected_payload("teams")


def test_both_renderers_preserve_required_body_semantics() -> None:
    expected_body = _notification().body

    assert _contains_text(_render(SlackTextRenderer()), expected_body)
    assert _contains_text(_render(TeamsTextRenderer()), expected_body)
