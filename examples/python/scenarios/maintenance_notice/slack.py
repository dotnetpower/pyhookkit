"""Render or send the maintenance notice for Slack."""

from example_notification import build_notification

from pyhookkit.adapters.outbound.slack.identity import (
    SlackIdentity,
    SlackIdentityDirectory,
)
from pyhookkit.adapters.outbound.slack.message_renderer import SlackMessageRenderer
from pyhookkit.domain.notification import MentionKind
from pyhookkit.entrypoints.slack_webhook_example import run_slack_webhook_example


def main() -> None:
    identities = SlackIdentityDirectory(
        {
            "example-operations": SlackIdentity(
                MentionKind.GROUP,
                "S00000118",
            )
        }
    )
    run_slack_webhook_example(
        build_notification(),
        SlackMessageRenderer(identities),
    )


if __name__ == "__main__":
    main()
