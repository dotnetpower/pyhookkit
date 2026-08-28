"""Check Slack bot authentication without printing the token."""

import argparse
import json

from pyhookkit.adapters.outbound.slack.workspace_directory import (
    SlackWorkspaceDirectory,
)
from pyhookkit.entrypoints.slack_web_api import slack_web_api_from_environment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    arguments = parser.parse_args()
    if not arguments.live:
        print(json.dumps({"method": "auth.test", "live": False}, indent=2))
        return

    workspace = SlackWorkspaceDirectory(slack_web_api_from_environment()).workspace()
    print(
        json.dumps(
            {
                "teamId": workspace.team_id,
                "teamName": workspace.team_name,
                "userId": workspace.user_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
