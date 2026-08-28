"""Render or send an interactive Slack approval request."""

import argparse
import json

from pyhookkit.adapters.outbound.slack.approval_renderer import (
    SlackApprovalRenderer,
)
from pyhookkit.adapters.outbound.slack.message_service import SlackMessageService
from pyhookkit.domain.notification import CanonicalNotification, Fact, Severity
from pyhookkit.entrypoints.slack_web_api import (
    required_slack_environment,
    slack_web_api_from_environment,
)


def build_notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-approval-001",
        route="release-approvals",
        title="Release approval requested",
        body="Approve or reject the synthetic production release.",
        severity=Severity.WARNING,
        facts=(Fact("Version", "v1.2.3-example"),),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true")
    arguments = parser.parse_args()
    payload = SlackApprovalRenderer().render(build_notification())
    if not arguments.send:
        print(json.dumps(payload, indent=2))
        return
    reference = SlackMessageService(slack_web_api_from_environment()).post(
        required_slack_environment("SLACK_CHANNEL_ID"),
        payload,
    )
    print(
        json.dumps(
            {
                "state": "succeeded",
                "channelId": reference.channel_id,
                "messageTs": reference.message_ts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
