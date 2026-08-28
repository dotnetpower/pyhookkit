"""Standalone Teams Adaptive Card example entrypoint tests."""

import json
from pathlib import Path

import pytest

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
