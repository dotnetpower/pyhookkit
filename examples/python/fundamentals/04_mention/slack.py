"""Render or send logical mentions for Slack."""

import os
import sys

from example_notification import build_notification

from pyhookkit.adapters.outbound.slack.identity import (
    SlackIdentity,
    SlackIdentityDirectory,
    SlackIdentityNotFoundError,
)
from pyhookkit.adapters.outbound.slack.message_renderer import (
    SlackMessageRenderer,
)
from pyhookkit.domain.notification import MentionKind
from pyhookkit.entrypoints.slack_webhook_example import (
    run_slack_webhook_example,
)


def main() -> None:
    user_id = _identity("SLACK_USER_ID", "U00000001")
    group_id = _identity("SLACK_USER_GROUP_ID", "S00000001")
    identities = SlackIdentityDirectory(
        {
            "example-owner": SlackIdentity(MentionKind.USER, user_id),
            "example-responders": SlackIdentity(MentionKind.GROUP, group_id),
        }
    )
    run_slack_webhook_example(
        build_notification(),
        SlackMessageRenderer(identities),
    )


def _identity(variable_name: str, synthetic_value: str) -> str:
    value = os.environ.get(variable_name, "").strip()
    if value:
        return value
    if "--send" in sys.argv[1:]:
        raise SlackIdentityNotFoundError(
            f"{variable_name} is required when sending the mention example"
        )
    return synthetic_value


if __name__ == "__main__":
    main()
