#!/usr/bin/env python3
"""Prepare Power Platform deployment settings for routed Teams delivery."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import UUID

type JsonValue = (
    bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None
)

TEAMS_CONNECTOR_ID = "/providers/Microsoft.PowerApps/apis/shared_teams"
SIGNED_URL_PATTERN = re.compile(r"https://[^\s]+[?&](?:sig|code)=", re.IGNORECASE)


class DeploymentSettingsError(ValueError):
    """Raised when generated deployment settings violate the expected contract."""


def prepare_settings(
    document: JsonValue,
    *,
    teams_connection_id: str,
    allowed_channel_links_schema_name: str,
    allowed_channel_links: tuple[str, ...],
) -> dict[str, JsonValue]:
    """Bind one Teams connection and an exact channel-link allowlist."""
    if not isinstance(document, dict):
        raise DeploymentSettingsError("deployment settings must be a JSON object")
    if not teams_connection_id.strip():
        raise DeploymentSettingsError("Teams connection ID must not be blank")
    if not allowed_channel_links:
        raise DeploymentSettingsError("at least one allowed channel link is required")
    if len(set(allowed_channel_links)) != len(allowed_channel_links):
        raise DeploymentSettingsError("allowed channel links must be unique")
    for channel_link in allowed_channel_links:
        _validate_channel_link(channel_link)
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
    _set_environment_value(
        environment_variables,
        allowed_channel_links_schema_name,
        json.dumps(allowed_channel_links, separators=(",", ":")),
    )
    return document


def _validate_channel_link(channel_link: str) -> None:
    parsed = urlsplit(channel_link)
    path_parts = parsed.path.split("/")
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "teams.microsoft.com"
        or parsed.fragment
        or len(path_parts) != 5
        or path_parts[1:3] != ["l", "channel"]
        or re.fullmatch(
            r"19:[A-Za-z0-9_-]+@thread\.(?:tacv2|skype)",
            unquote(path_parts[3]),
        )
        is None
        or not unquote(path_parts[4]).strip()
    ):
        raise DeploymentSettingsError("invalid Microsoft Teams channel link")
    query = parse_qs(parsed.query, strict_parsing=True)
    for parameter in ("groupId", "tenantId"):
        values = query.get(parameter, [])
        if len(values) != 1:
            raise DeploymentSettingsError("invalid Microsoft Teams channel link")
        try:
            UUID(values[0])
        except ValueError as error:
            raise DeploymentSettingsError(
                "invalid Microsoft Teams channel link"
            ) from error


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
    parser.add_argument("--allowed-channel-links-schema-name", required=True)
    parser.add_argument("--allowed-channel-link", action="append", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    with args.input.open(encoding="utf-8") as source:
        document = cast(JsonValue, json.load(source))
    prepared = prepare_settings(
        document,
        teams_connection_id=args.teams_connection_id,
        allowed_channel_links_schema_name=args.allowed_channel_links_schema_name,
        allowed_channel_links=tuple(args.allowed_channel_link),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        json.dump(prepared, destination, indent=2)
        destination.write("\n")
    print(f"Prepared deployment settings: {args.output}")


if __name__ == "__main__":
    main()
