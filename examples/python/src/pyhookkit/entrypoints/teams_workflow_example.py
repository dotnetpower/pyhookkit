"""CLI composition for renderable Microsoft Teams Workflow examples."""

import argparse
import json
import os
from collections.abc import Mapping, Sequence

from pyhookkit.adapters.outbound.delivery_result_json import (
    delivery_result_to_json,
)
from pyhookkit.adapters.outbound.teams.channel_link import TeamsChannelLink
from pyhookkit.adapters.outbound.teams.route_resolver import (
    TeamsEnvironmentRouteResolver,
)
from pyhookkit.adapters.outbound.teams.workflow_destination import (
    TeamsWorkflowDestination,
)
from pyhookkit.adapters.outbound.teams.workflow_request import (
    build_teams_workflow_request,
)
from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.domain.delivery import DeliveryState
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.entrypoints.example_asset import resolve_example_asset_urls
from pyhookkit.entrypoints.teams_logic_app_example import (
    send_teams_logic_app_example,
)
from pyhookkit.ports.message_renderer import MessageRenderer

_CHANNEL_LINK_VARIABLE = "TEAMS_WORKFLOW_CHANNEL_LINK"


def run_teams_workflow_example(
    notification: CanonicalNotification,
    renderer: MessageRenderer,
    *,
    arguments: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Render or deliberately send one Teams Workflow example."""
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check-route", action="store_true")
    action.add_argument("--send", action="store_true")
    action.add_argument("--send-logic-app", action="store_true")
    parsed = parser.parse_args(arguments)
    active_environment = os.environ if environment is None else environment
    resolver = TeamsEnvironmentRouteResolver({notification.route: "TEAMS_WORKFLOW_URL"})
    if parsed.check_route:
        TeamsWorkflowUrl(resolver.resolve(notification.route, active_environment))
        _channel_link(active_environment)
        print("Teams route configured")
        return

    payload = renderer.render(notification)
    if not parsed.send and not parsed.send_logic_app:
        print(json.dumps(payload, indent=2))
        return

    if parsed.send_logic_app:
        send_teams_logic_app_example(
            payload,
            event_id=notification.event_id,
            environment=active_environment,
        )
        return

    raw_url = resolver.resolve(notification.route, active_environment)
    payload = resolve_example_asset_urls(payload, environment=active_environment)
    request = build_teams_workflow_request(
        payload,
        _channel_link(active_environment),
    )
    result = TeamsWorkflowDestination(TeamsWorkflowUrl(raw_url)).send(request)
    print(json.dumps(delivery_result_to_json(result), indent=2))
    if result.state is DeliveryState.FAILED:
        raise SystemExit(1)


def _channel_link(environment: Mapping[str, str]) -> TeamsChannelLink:
    raw_link = environment.get(_CHANNEL_LINK_VARIABLE, "").strip()
    if not raw_link:
        raise ValueError(f"{_CHANNEL_LINK_VARIABLE} is required for Workflow delivery")
    return TeamsChannelLink(raw_link)
