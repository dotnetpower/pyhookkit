"""Slack Web API environment composition tests."""

import pytest

from pyhookkit.entrypoints.slack_web_api import (
    SlackEnvironmentError,
    required_slack_environment,
    slack_socket_api_from_environment,
    slack_web_api_from_environment,
)

_BOT_TOKEN = "xoxb-000000000000-synthetic"
_APP_TOKEN = "xapp-000000000000-synthetic"


def test_bot_and_socket_clients_are_composed_from_environment() -> None:
    bot_client = slack_web_api_from_environment({"SLACK_BOT_TOKEN": _BOT_TOKEN})
    socket_client = slack_socket_api_from_environment({"SLACK_APP_TOKEN": _APP_TOKEN})

    assert _BOT_TOKEN not in repr(bot_client)
    assert _APP_TOKEN not in repr(socket_client)


def test_required_environment_strips_non_secret_values() -> None:
    assert (
        required_slack_environment(
            "SLACK_CHANNEL_ID",
            environment={"SLACK_CHANNEL_ID": " C00000001 "},
        )
        == "C00000001"
    )


@pytest.mark.parametrize(
    "environment",
    [{}, {"SLACK_CHANNEL_ID": ""}, {"SLACK_CHANNEL_ID": "  "}],
)
def test_required_environment_rejects_missing_values(
    environment: dict[str, str],
) -> None:
    with pytest.raises(SlackEnvironmentError, match="SLACK_CHANNEL_ID"):
        required_slack_environment(
            "SLACK_CHANNEL_ID",
            environment=environment,
        )
