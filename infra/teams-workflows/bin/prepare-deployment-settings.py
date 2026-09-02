#!/usr/bin/env python3
"""Prepare Power Platform deployment settings for Teams Workflow delivery."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import cast

type JsonValue = (
    bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None
)

TEAMS_CONNECTOR_ID = "/providers/Microsoft.PowerApps/apis/shared_teams"
SIGNED_URL_PATTERN = re.compile(r"https://[^\s]+[?&](?:sig|code)=", re.IGNORECASE)
TEAM_ID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.IGNORECASE,
)


class DeploymentSettingsError(ValueError):
    """Raised when generated deployment settings violate the expected contract."""


def prepare_settings(
    document: JsonValue,
    *,
    teams_connection_id: str,
    team_schema_name: str,
    team_id: str,
    channel_schema_name: str,
    channel_id: str,
) -> dict[str, JsonValue]:
    """Bind one Teams connection and two destination environment variables."""
    if not isinstance(document, dict):
        raise DeploymentSettingsError("deployment settings must be a JSON object")
    if not TEAM_ID_PATTERN.fullmatch(team_id):
        raise DeploymentSettingsError("team ID must be a GUID")
    if not channel_id.strip():
        raise DeploymentSettingsError("channel ID must not be blank")
    if not teams_connection_id.strip():
        raise DeploymentSettingsError("Teams connection ID must not be blank")
    if SIGNED_URL_PATTERN.search(json.dumps(document)):
        raise DeploymentSettingsError("deployment settings contain a signed URL")

    connection_references = _object_list(document, "ConnectionReferences")
    teams_references = [
        reference
        for reference in connection_references
        if reference.get("ConnectorId") == TEAMS_CONNECTOR_ID
    ]
    if len(teams_references) != 1:
        raise DeploymentSettingsError(
            "deployment settings must contain exactly one Microsoft Teams "
            "connection reference"
        )
    teams_references[0]["ConnectionId"] = teams_connection_id

    environment_variables = _object_list(document, "EnvironmentVariables")
    _set_environment_value(environment_variables, team_schema_name, team_id)
    _set_environment_value(environment_variables, channel_schema_name, channel_id)
    return document


def _object_list(
    document: dict[str, JsonValue], key: str
) -> list[dict[str, JsonValue]]:
    value = document.get(key)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise DeploymentSettingsError(f"{key} must be an array of objects")
    return cast(list[dict[str, JsonValue]], value)


def _set_environment_value(
    variables: list[dict[str, JsonValue]], schema_name: str, value: str
) -> None:
    matches = [item for item in variables if item.get("SchemaName") == schema_name]
    if len(matches) != 1:
        raise DeploymentSettingsError(
            f"environment variable {schema_name!r} must occur exactly once"
        )
    matches[0]["Value"] = value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--teams-connection-id", required=True)
    parser.add_argument("--team-schema-name", required=True)
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--channel-schema-name", required=True)
    parser.add_argument("--channel-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    with args.input.open(encoding="utf-8") as source:
        document = cast(JsonValue, json.load(source))
    prepared = prepare_settings(
        document,
        teams_connection_id=args.teams_connection_id,
        team_schema_name=args.team_schema_name,
        team_id=args.team_id,
        channel_schema_name=args.channel_schema_name,
        channel_id=args.channel_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        json.dump(prepared, destination, indent=2)
        destination.write("\n")
    print(f"Prepared deployment settings: {args.output}")


if __name__ == "__main__":
    main()
