"""Resolve a Slack user and enumerate mentionable user groups."""

import argparse
import json

from pyhookkit.adapters.outbound.slack.message_service import SlackMessageService
from pyhookkit.adapters.outbound.slack.workspace_directory import (
    SlackWorkspaceDirectory,
)
from pyhookkit.entrypoints.slack_web_api import (
    required_slack_environment,
    slack_web_api_from_environment,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--display-name")
    parser.add_argument("--send-mention", action="store_true")
    arguments = parser.parse_args()
    if not arguments.live:
        print(
            json.dumps(
                {
                    "methods": ["users.list", "usergroups.list"],
                    "live": False,
                },
                indent=2,
            )
        )
        return

    display_name = arguments.display_name or required_slack_environment(
        "SLACK_TEST_DISPLAY_NAME"
    )
    directory = SlackWorkspaceDirectory(slack_web_api_from_environment())
    user = directory.find_active_user(display_name)
    groups = directory.user_groups()
    if arguments.send_mention:
        reference = SlackMessageService(slack_web_api_from_environment()).post(
            required_slack_environment("SLACK_CHANNEL_ID"),
            {"text": f"Hello <@{user.identifier}> from PyHookKit."},
        )
        print(
            json.dumps(
                {
                    "state": "succeeded",
                    "channelId": reference.channel_id,
                    "messageTs": reference.message_ts,
                    "userId": user.identifier,
                },
                indent=2,
            )
        )
        return
    print(
        json.dumps(
            {
                "user": {
                    "id": user.identifier,
                    "displayName": user.display_name,
                    "mention": f"<@{user.identifier}>",
                },
                "groups": [
                    {
                        "id": group.identifier,
                        "handle": group.handle,
                        "mention": f"<!subteam^{group.identifier}>",
                    }
                    for group in groups
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
