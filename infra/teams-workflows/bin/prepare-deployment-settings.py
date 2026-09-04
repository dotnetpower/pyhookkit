#!/usr/bin/env python3
"""Prepare Power Platform deployment settings for routed Teams delivery."""

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


class DeploymentSettingsError(ValueError):
    """Raised when generated deployment settings violate the expected contract."""


def prepare_settings(
    document: JsonValue,
    *,
    teams_connection_id: str,
) -> dict[str, JsonValue]:
    """Bind one Microsoft Teams connection reference."""
    if not isinstance(document, dict):
        raise DeploymentSettingsError("deployment settings must be a JSON object")
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

    return document


def _object_list(
    document: dict[str, JsonValue], key: str
) -> list[dict[str, JsonValue]]:
    value = document.get(key)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise DeploymentSettingsError(f"{key} must be an array of objects")
    return cast(list[dict[str, JsonValue]], value)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--teams-connection-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    with args.input.open(encoding="utf-8") as source:
        document = cast(JsonValue, json.load(source))
    prepared = prepare_settings(
        document,
        teams_connection_id=args.teams_connection_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        json.dump(prepared, destination, indent=2)
        destination.write("\n")
    print(f"Prepared deployment settings: {args.output}")


if __name__ == "__main__":
    main()
