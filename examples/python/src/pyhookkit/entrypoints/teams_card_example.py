"""CLI composition for standalone Microsoft Teams Adaptive Card examples."""

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from pyhookkit.adapters.outbound.delivery_result_json import (
    delivery_result_to_json,
)
from pyhookkit.adapters.outbound.teams.workflow_destination import (
    TeamsWorkflowDestination,
)
from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.domain.delivery import DeliveryState
from pyhookkit.entrypoints.example_asset import resolve_example_asset_urls
from pyhookkit.entrypoints.teams_logic_app_example import (
    send_teams_logic_app_example,
)
from pyhookkit.json_types import JsonObject, JsonValue


class TeamsCardExampleError(ValueError):
    """A standalone Teams card example is malformed."""


def load_teams_card(
    path: Path,
    *,
    replacements: Mapping[str, str] | None = None,
) -> JsonObject:
    with path.open(encoding="utf-8") as file:
        value: object = json.load(file)
    payload = _json_value(value, path)
    if not isinstance(payload, dict):
        raise TeamsCardExampleError(f"{path} must contain a JSON object")
    if replacements is not None:
        payload = cast(
            JsonObject,
            _replace_strings(payload, replacements),
        )
    _validate_teams_envelope(payload)
    return payload


def run_teams_card_file_example(
    path: Path,
    *,
    arguments: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
    replacements: Mapping[str, str] | None = None,
    event_id: str | None = None,
) -> None:
    run_teams_card_example(
        load_teams_card(path, replacements=replacements),
        arguments=arguments,
        environment=environment,
        event_id=event_id,
    )


def run_teams_card_example(
    payload: JsonObject,
    *,
    arguments: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
    event_id: str | None = None,
) -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--send", action="store_true")
    action.add_argument("--send-logic-app", action="store_true")
    parsed = parser.parse_args(arguments)
    _validate_teams_envelope(payload)
    if not parsed.send and not parsed.send_logic_app:
        print(json.dumps(payload, indent=2))
        return

    active_environment = os.environ if environment is None else environment
    if parsed.send_logic_app:
        send_teams_logic_app_example(
            payload,
            event_id=event_id,
            environment=active_environment,
        )
        return

    raw_url = active_environment.get("TEAMS_WORKFLOW_URL", "").strip()
    if not raw_url:
        raise TeamsCardExampleError("TEAMS_WORKFLOW_URL is required with --send")
    payload = resolve_example_asset_urls(payload, environment=active_environment)
    result = TeamsWorkflowDestination(TeamsWorkflowUrl(raw_url)).send(payload)
    print(json.dumps(delivery_result_to_json(result), indent=2))
    if result.state is DeliveryState.FAILED:
        raise SystemExit(1)


def _validate_teams_envelope(payload: JsonObject) -> None:
    if payload.get("type") != "message":
        raise TeamsCardExampleError("Teams card envelope type must be message")
    attachments = payload.get("attachments")
    if not isinstance(attachments, list) or len(attachments) != 1:
        raise TeamsCardExampleError(
            "Teams card envelope requires exactly one attachment"
        )
    attachment = attachments[0]
    if (
        not isinstance(attachment, dict)
        or attachment.get("contentType") != "application/vnd.microsoft.card.adaptive"
    ):
        raise TeamsCardExampleError(
            "Teams card attachment must contain Adaptive Card content"
        )
    content = attachment.get("content")
    if (
        not isinstance(content, dict)
        or content.get("type") != "AdaptiveCard"
        or not isinstance(content.get("body"), list)
        or not isinstance(content.get("fallbackText"), str)
    ):
        raise TeamsCardExampleError("Teams Adaptive Card content is incomplete")


def _json_value(value: object, path: Path) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        return [_json_value(item, path) for item in cast(list[object], value)]
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        if not all(isinstance(key, str) for key in mapping):
            raise TeamsCardExampleError(f"{path} must contain only string keys")
        return {
            cast(str, key): _json_value(item, path) for key, item in mapping.items()
        }
    raise TeamsCardExampleError(f"{path} contains a non-JSON value")


def _replace_strings(
    value: JsonValue,
    replacements: Mapping[str, str],
) -> JsonValue:
    if isinstance(value, str):
        result = value
        for marker, replacement in replacements.items():
            result = result.replace(marker, replacement)
        return result
    if isinstance(value, list):
        return [_replace_strings(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            key: _replace_strings(item, replacements) for key, item in value.items()
        }
    return value
