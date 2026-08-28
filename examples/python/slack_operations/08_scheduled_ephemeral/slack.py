"""Exercise scheduled and user-targeted ephemeral Slack messages."""

import argparse
import json
from datetime import UTC, datetime, timedelta

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
    parser.add_argument("--exercise", action="store_true")
    parser.add_argument("--display-name")
    arguments = parser.parse_args()
    if not arguments.exercise:
        print(
            json.dumps(
                {
                    "methods": [
                        "chat.scheduleMessage",
                        "chat.deleteScheduledMessage",
                        "chat.postEphemeral",
                    ],
                    "live": False,
                },
                indent=2,
            )
        )
        return

    api = slack_web_api_from_environment()
    channel_id = required_slack_environment("SLACK_CHANNEL_ID")
    display_name = arguments.display_name or required_slack_environment(
        "SLACK_TEST_DISPLAY_NAME"
    )
    user = SlackWorkspaceDirectory(api).find_active_user(display_name)
    service = SlackMessageService(api)
    scheduled = service.schedule(
        channel_id,
        datetime.now(tz=UTC) + timedelta(minutes=5),
        {"text": "Synthetic maintenance reminder."},
    )
    service.delete_scheduled(scheduled)
    ephemeral_ts = service.post_ephemeral(
        channel_id,
        user.identifier,
        {"text": "Synthetic private delivery confirmation."},
    )
    print(
        json.dumps(
            {
                "state": "succeeded",
                "scheduledMessageDeleted": True,
                "ephemeralMessageTs": ephemeral_ts,
                "userId": user.identifier,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
