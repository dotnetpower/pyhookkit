"""Semantic parity tests for paired fundamental notification examples."""

import json
from pathlib import Path

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_VECTOR_ROOT = _REPOSITORY_ROOT / "contracts" / "test-vectors" / "fundamentals"

_COMMON_SEMANTICS = {
    "mention": (
        "Action required",
        "Review the synthetic alert.",
    ),
    "link-and-action": (
        "Investigation available",
        "Open the synthetic investigation details.",
        "View details",
        "https://example.com/notifications/example-001",
    ),
    "routing": (
        "Routed notification",
        "This notification uses a logical destination.",
    ),
    "thread-or-reply": ("Synthetic follow-up completed.",),
    "update-and-delete": (
        "Status corrected",
        "The synthetic status has been corrected.",
    ),
    "error-and-retry": ("Synthetic retry verification.",),
}


def _slack_payload(capability: str) -> str:
    directory = _VECTOR_ROOT / capability
    if capability == "update-and-delete":
        payloads = [
            json.loads((directory / filename).read_text())
            for filename in ("slack.update.expected.json", "slack.delete.expected.json")
        ]
        return json.dumps(payloads)
    return (directory / "slack.expected.json").read_text()


@pytest.mark.parametrize("capability", _COMMON_SEMANTICS)
def test_required_meaning_survives_both_providers(capability: str) -> None:
    slack_payload = _slack_payload(capability)
    teams_payload = (_VECTOR_ROOT / capability / "teams.expected.json").read_text()

    for value in _COMMON_SEMANTICS[capability]:
        assert value in slack_payload
        assert value in teams_payload


def test_teams_workflow_differences_are_explicit() -> None:
    thread_payload = (
        _VECTOR_ROOT / "thread-or-reply" / "teams.expected.json"
    ).read_text()
    mutation_payload = (
        _VECTOR_ROOT / "update-and-delete" / "teams.expected.json"
    ).read_text()

    assert "cannot target a parent message" in thread_payload
    assert "example-deployment-001" in thread_payload
    assert "cannot update or delete" in mutation_payload


def test_mentions_preserve_user_intent() -> None:
    slack_payload = _slack_payload("mention")
    teams_payload = (_VECTOR_ROOT / "mention" / "teams.expected.json").read_text()

    assert "<@U00000001>" in slack_payload
    assert "<!subteam^S00000001>" in slack_payload
    assert "<at>Example Owner</at>" in teams_payload
    assert "example-responders" not in teams_payload
