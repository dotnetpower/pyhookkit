"""Use reactions as transient notification processing status."""

import argparse
import json

from pyhookkit.adapters.outbound.slack.message_service import SlackMessageService
from pyhookkit.entrypoints.slack_web_api import (
    required_slack_environment,
    slack_web_api_from_environment,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exercise", action="store_true")
    arguments = parser.parse_args()
    if not arguments.exercise:
        print(
            json.dumps(
                {
                    "methods": [
                        "chat.postMessage",
                        "reactions.add",
                        "reactions.remove",
                        "chat.delete",
                    ],
                    "live": False,
                },
                indent=2,
            )
        )
        return

    service = SlackMessageService(slack_web_api_from_environment())
    reference = service.post(
        required_slack_environment("SLACK_CHANNEL_ID"),
        {"text": "Synthetic notification processing."},
    )
    service.add_reaction(reference, "hourglass_flowing_sand")
    service.remove_reaction(reference, "hourglass_flowing_sand")
    service.add_reaction(reference, "white_check_mark")
    print(
        json.dumps(
            {
                "state": "succeeded",
                "channelId": reference.channel_id,
                "messageTs": reference.message_ts,
                "reaction": "white_check_mark",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
