"""Azure Logic App workflow definition contract tests."""

import json
from pathlib import Path
from typing import cast

from pyhookkit.json_types import JsonObject

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_DEFINITION_PATH = (
    _REPOSITORY_ROOT / "infra" / "azure" / "logic-apps" / "workflow-definition.json"
)


def _definition() -> JsonObject:
    value: object = json.loads(_DEFINITION_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(JsonObject, value)


def test_logic_app_requires_routing_and_card() -> None:
    trigger = _definition()["triggers"]
    assert isinstance(trigger, dict)
    request = trigger["When_a_HTTP_request_is_received"]
    assert isinstance(request, dict)
    inputs = request["inputs"]
    assert isinstance(inputs, dict)
    schema = inputs["schema"]
    assert isinstance(schema, dict)

    assert schema["additionalProperties"] is False
    assert schema["required"] == ["teamId", "channelId", "card"]


def test_logic_app_secures_provider_data_and_returns_explicit_statuses() -> None:
    definition = _definition()
    trigger = definition["triggers"]
    assert isinstance(trigger, dict)
    request = trigger["When_a_HTTP_request_is_received"]
    assert isinstance(request, dict)
    trigger_runtime = request["runtimeConfiguration"]
    assert isinstance(trigger_runtime, dict)
    assert trigger_runtime["secureData"] == {"properties": ["inputs", "outputs"]}

    actions = definition["actions"]
    assert isinstance(actions, dict)
    validation = actions["Validate_request"]
    assert isinstance(validation, dict)
    valid_actions = validation["actions"]
    assert isinstance(valid_actions, dict)
    post = valid_actions["Post_card_to_channel"]
    assert isinstance(post, dict)
    post_runtime = post["runtimeConfiguration"]
    assert isinstance(post_runtime, dict)
    assert post_runtime["secureData"] == {"properties": ["inputs", "outputs"]}

    created = valid_actions["Response_created"]
    connector_error = valid_actions["Response_connector_error"]
    invalid_actions = validation["else"]
    assert isinstance(created, dict)
    assert isinstance(connector_error, dict)
    assert isinstance(invalid_actions, dict)
    invalid = invalid_actions["actions"]
    assert isinstance(invalid, dict)
    bad_request = invalid["Response_bad_request"]
    assert isinstance(bad_request, dict)

    for action, status in ((created, 201), (connector_error, 502), (bad_request, 400)):
        inputs = action["inputs"]
        assert isinstance(inputs, dict)
        assert inputs["statusCode"] == status
