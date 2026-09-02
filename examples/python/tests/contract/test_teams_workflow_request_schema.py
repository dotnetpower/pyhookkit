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


def _validator() -> Validator:
    return Draft202012Validator(
        _load_json(_SCHEMA_PATH),
        format_checker=FormatChecker(),
    )


def test_routed_workflow_request_matches_schema() -> None:
    envelope: JsonObject = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {"type": "AdaptiveCard"},
            }
        ],
    }

    request = build_teams_workflow_request(envelope, TeamsChannelLink(_LINK))

    _validator().validate(request)


def test_routed_workflow_schema_requires_channel_link() -> None:
    schema = _load_json(_SCHEMA_PATH)

    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "type",
        "channelLink",
        "teamId",
        "channelId",
        "attachments",
    ]
