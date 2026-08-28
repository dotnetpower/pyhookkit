"""Standalone Teams Adaptive Card example entrypoint tests."""

import json
from pathlib import Path

import pytest

import pyhookkit.entrypoints.teams_card_example as entrypoint
from pyhookkit.entrypoints.teams_card_example import (
    TeamsCardExampleError,
    load_teams_card,
    run_teams_card_example,
)
from pyhookkit.json_types import JsonObject


def _payload() -> JsonObject:
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "fallbackText": "Synthetic card",
                    "body": [{"type": "TextBlock", "text": "Synthetic card"}],
                },
            }
        ],
    }


def test_entrypoint_renders_valid_card(
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_teams_card_example(_payload(), arguments=[], environment={})

    assert json.loads(capsys.readouterr().out) == _payload()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"type": "message", "attachments": []},
        {
            "type": "message",
            "attachments": [{"contentType": "text/plain"}],
        },
    ],
)
def test_entrypoint_rejects_malformed_envelopes(payload: JsonObject) -> None:
    with pytest.raises(TeamsCardExampleError):
        run_teams_card_example(payload, arguments=[])


def test_loader_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / "card.json"
    path.write_text("[]")

    with pytest.raises(TeamsCardExampleError, match="JSON object"):
        load_teams_card(path)


def test_card_entrypoint_routes_logic_app_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def send_logic_app(
        payload: JsonObject,
        *,
        event_id: str | None,
        environment: dict[str, str],
    ) -> None:
        captured["payload"] = payload
        captured["event_id"] = event_id
        captured["environment"] = environment

    monkeypatch.setattr(entrypoint, "send_teams_logic_app_example", send_logic_app)
    environment = {"TEAMS_LOGIC_APP_URL": "synthetic"}

    run_teams_card_example(
        _payload(),
        arguments=["--send-logic-app"],
        environment=environment,
        event_id="gallery-example",
    )

    assert captured["event_id"] == "gallery-example"
    assert captured["environment"] is environment
