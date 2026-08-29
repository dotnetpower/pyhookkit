"""CLI composition for renderable Slack webhook examples."""

import argparse
import json
import os
from collections.abc import Mapping, Sequence

from pyhookkit.adapters.outbound.delivery_result_json import (
    delivery_result_to_json,
)
from pyhookkit.adapters.outbound.slack.route_resolver import (
    SlackEnvironmentRouteResolver,
)
from pyhookkit.adapters.outbound.slack.webhook_destination import (
    SlackWebhookDestination,
)
from pyhookkit.adapters.outbound.slack.webhook_url import SlackWebhookUrl
from pyhookkit.domain.delivery import DeliveryState
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.entrypoints.example_asset import resolve_example_asset_urls
from pyhookkit.ports.message_renderer import MessageRenderer


def run_slack_webhook_example(
    notification: CanonicalNotification,
    renderer: MessageRenderer,
    *,
    arguments: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Render, validate, or deliberately send one Slack example."""
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check-route", action="store_true")
    action.add_argument("--send", action="store_true")
    parsed = parser.parse_args(arguments)

    active_environment = os.environ if environment is None else environment
    resolver = SlackEnvironmentRouteResolver({notification.route: "SLACK_WEBHOOK_URL"})
    if parsed.check_route:
        SlackWebhookUrl(resolver.resolve(notification.route, active_environment))
        print("Slack route configured")
        return

    payload = renderer.render(notification)
    if not parsed.send:
        print(json.dumps(payload, indent=2))
        return

    webhook_url = SlackWebhookUrl(
        resolver.resolve(notification.route, active_environment)
    )
    payload = resolve_example_asset_urls(payload, environment=active_environment)
    result = SlackWebhookDestination(webhook_url).send(payload)
    print(json.dumps(delivery_result_to_json(result), indent=2))
    if result.state is DeliveryState.FAILED:
        raise SystemExit(1)
