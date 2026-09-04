"""Routed Power Automate request schema tests."""

import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.protocols import Validator

from pyhookkit.adapters.outbound.teams.channel_link import TeamsChannelLink
from pyhookkit.adapters.outbound.teams.workflow_request import (
    build_teams_workflow_request,
)
from pyhookkit.json_types import JsonObject

type SchemaObject = dict[str, Any]

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_PATH = (
    _REPOSITORY_ROOT / "infra" / "teams-workflows" / "routed-request.schema.json"
)
_POWER_AUTOMATE_SCHEMA_PATH = (
    _REPOSITORY_ROOT
    / "infra"
    / "teams-workflows"
    / "power-automate-trigger.schema.json"
)
_LINK = (
    "https://teams.microsoft.com/l/channel/"
    "19%3Aexample-channel%40thread.tacv2/General"
    "?groupId=11111111-1111-4111-8111-111111111111"
    "&tenantId=22222222-2222-4222-8222-222222222222"
)


def _load_json(path: Path) -> SchemaObject:
    with path.open(encoding="utf-8") as file:
        value: object = json.load(file)
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    mapping = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in mapping):
        raise TypeError(f"{path} must contain only string keys")
    return cast(SchemaObject, mapping)


def _validator(path: Path = _SCHEMA_PATH) -> Validator:
    return Draft202012Validator(
        _load_json(path),
        format_checker=FormatChecker(),
    )


def test_routed_workflow_request_matches_schema() -> None:
    envelope: JsonObject = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [],
                },
            }
        ],
    }

    channel_link = TeamsChannelLink(_LINK)
    request = build_teams_workflow_request(
        envelope,
        team_id=channel_link.team_id,
        channel_id=channel_link.channel_id,
    )

    _validator().validate(request)
    _validator(_POWER_AUTOMATE_SCHEMA_PATH).validate(request)


def test_routed_workflow_schema_requires_card_and_target() -> None:
    schema = _load_json(_SCHEMA_PATH)

    assert schema["required"] == [
        "type",
        "version",
        "body",
        "teamId",
        "channelId",
    ]


def test_power_automate_schema_preserves_required_fields_without_patterns() -> None:
    canonical_schema = _load_json(_SCHEMA_PATH)
    trigger_schema = _load_json(_POWER_AUTOMATE_SCHEMA_PATH)

    assert trigger_schema["required"] == canonical_schema["required"]
    assert trigger_schema["properties"].keys() == canonical_schema["properties"].keys()
    assert "pattern" not in json.dumps(trigger_schema)
    assert "format" not in trigger_schema["properties"]["teamId"]
