"""Exercise Slack post, reply, update, and delete operations."""

import argparse
import json

from pyhookkit.adapters.outbound.slack.message_renderer import SlackMessageRenderer
from pyhookkit.adapters.outbound.slack.message_service import SlackMessageService
from pyhookkit.domain.notification import CanonicalNotification, Severity
from pyhookkit.entrypoints.slack_web_api import (
    required_slack_environment,
    slack_web_api_from_environment,
)


def _notification(body: str) -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-lifecycle-001",
        route="platform-alerts",
        title="Synthetic lifecycle",
        body=body,
        severity=Severity.INFO,
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
                        "chat.postMessage(thread_ts)",
                        "chat.update",
                        "chat.delete",
                    ],
                    "live": False,
                },
                indent=2,
            )
        )
        return

    channel_id = required_slack_environment("SLACK_CHANNEL_ID")
    renderer = SlackMessageRenderer()
    service = SlackMessageService(slack_web_api_from_environment())
    parent = service.post(
        channel_id,
        renderer.render(_notification("Lifecycle started.")),
    )
    reply = service.post(
        channel_id,
        {"text": "Synthetic acknowledgment."},
        parent=parent,
    )
    service.update(
        parent,
        renderer.render(_notification("Lifecycle completed.")),
    )
    service.delete(reply)
    print(
        json.dumps(
            {
                "state": "succeeded",
                "channelId": parent.channel_id,
                "messageTs": parent.message_ts,
                "replyDeleted": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
