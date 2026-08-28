"""Slack logical route tests."""

import pytest

from pyhookkit.adapters.outbound.slack.route_resolver import (
    SlackEnvironmentRouteResolver,
    SlackRouteNotConfiguredError,
)
from pyhookkit.adapters.outbound.slack.webhook_url import SlackWebhookUrl


def test_route_resolves_environment_variable() -> None:
    resolver = SlackEnvironmentRouteResolver({"platform-alerts": "SLACK_WEBHOOK_URL"})

    result = resolver.resolve(
        "platform-alerts",
        {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/example"},
    )

    assert SlackWebhookUrl(result).value == result


def test_route_rejects_unknown_or_empty_configuration() -> None:
    resolver = SlackEnvironmentRouteResolver({"platform-alerts": "SLACK_WEBHOOK_URL"})

    with pytest.raises(SlackRouteNotConfiguredError, match="not configured"):
        resolver.resolve("unknown-route", {})
    with pytest.raises(SlackRouteNotConfiguredError, match="variable is empty"):
        resolver.resolve("platform-alerts", {"SLACK_WEBHOOK_URL": " "})


@pytest.mark.parametrize(
    "url",
    [
        "http://hooks.slack.com/services/example",
        "https://example.com/services/example",
        "https://hooks.slack.com/not-services/example",
    ],
)
def test_webhook_url_rejects_non_slack_destinations(url: str) -> None:
    with pytest.raises(ValueError, match="invalid Slack"):
        SlackWebhookUrl(url)
