"""List Slack channels or members with cursor pagination."""

import argparse
import json

from pyhookkit.adapters.outbound.slack.workspace_directory import (
    SlackWorkspaceDirectory,
)
from pyhookkit.entrypoints.slack_web_api import slack_web_api_from_environment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--members", metavar="CHANNEL_ID")
    arguments = parser.parse_args()
    if not arguments.live:
        print(
            json.dumps(
                {
                    "methods": ["conversations.list", "conversations.members"],
                    "live": False,
                },
                indent=2,
            )
        )
        return

    directory = SlackWorkspaceDirectory(slack_web_api_from_environment())
    if arguments.members is not None:
        print(
            json.dumps(
                {
                    "channelId": arguments.members,
                    "memberIds": directory.channel_members(arguments.members),
                },
                indent=2,
            )
        )
        return
    print(
        json.dumps(
            [
                {
                    "id": channel.identifier,
                    "name": channel.name,
                    "private": channel.is_private,
                    "member": channel.is_member,
                }
                for channel in directory.channels()
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
