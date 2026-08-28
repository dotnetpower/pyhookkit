"""Composition for sending rendered Teams cards through Azure Logic Apps."""

import json
from collections.abc import Mapping

from pyhookkit.adapters.outbound.delivery_result_json import delivery_result_to_json
from pyhookkit.adapters.outbound.teams.logic_app_destination import (
    TeamsLogicAppDestination,
)
from pyhookkit.adapters.outbound.teams.logic_app_request import (
    TeamsLogicAppTarget,
    build_teams_logic_app_request,
)
from pyhookkit.adapters.outbound.teams.logic_app_url import TeamsLogicAppUrl
from pyhookkit.domain.delivery import DeliveryState
from pyhookkit.entrypoints.example_asset import resolve_example_asset_urls
from pyhookkit.json_types import JsonObject

_URL_VARIABLE = "TEAMS_LOGIC_APP_URL"
_TEAM_VARIABLE = "TEAMS_LOGIC_APP_TEAM_ID"
_CHANNEL_VARIABLE = "TEAMS_LOGIC_APP_CHANNEL_ID"


def send_teams_logic_app_example(
    payload: JsonObject,
    *,
    event_id: str | None,
    environment: Mapping[str, str],
) -> None:
    """Adapt and send one rendered Teams card through the configured Logic App."""
    url = _required(environment, _URL_VARIABLE)
    target = TeamsLogicAppTarget(
        team_id=_required(environment, _TEAM_VARIABLE),
        channel_id=_required(environment, _CHANNEL_VARIABLE),
    )
    resolved_payload = resolve_example_asset_urls(payload, environment=environment)
    request = build_teams_logic_app_request(
        resolved_payload,
        target,
        event_id=event_id,
    )
    result = TeamsLogicAppDestination(TeamsLogicAppUrl(url)).send(request)
    print(json.dumps(delivery_result_to_json(result), indent=2))
    if result.state is DeliveryState.FAILED:
        raise SystemExit(1)


def _required(environment: Mapping[str, str], variable_name: str) -> str:
    value = environment.get(variable_name, "").strip()
    if not value:
        raise ValueError(f"{variable_name} is required with --send-logic-app")
    return value
