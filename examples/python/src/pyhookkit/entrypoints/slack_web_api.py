"""Slack Web API composition from environment configuration."""

import os
from collections.abc import Mapping

from pyhookkit.adapters.outbound.slack.web_api import (
    SlackAppToken,
    SlackBotToken,
    SlackWebApiClient,
)


class SlackEnvironmentError(ValueError):
    """Required Slack Web API configuration is absent."""


def slack_web_api_from_environment(
    environment: Mapping[str, str] | None = None,
) -> SlackWebApiClient:
    active_environment = os.environ if environment is None else environment
    token = required_slack_environment(
        "SLACK_BOT_TOKEN",
        environment=active_environment,
    )
    return SlackWebApiClient(SlackBotToken(token))


def slack_socket_api_from_environment(
    environment: Mapping[str, str] | None = None,
) -> SlackWebApiClient:
    active_environment = os.environ if environment is None else environment
    token = required_slack_environment(
        "SLACK_APP_TOKEN",
        environment=active_environment,
    )
    return SlackWebApiClient(SlackAppToken(token))


def required_slack_environment(
    name: str,
    *,
    environment: Mapping[str, str] | None = None,
) -> str:
    active_environment = os.environ if environment is None else environment
    value = active_environment.get(name, "").strip()
    if not value:
        raise SlackEnvironmentError(f"{name} is required")
    return value
