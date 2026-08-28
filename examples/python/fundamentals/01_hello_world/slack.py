"""Render or send the Hello World notification for Slack."""

from example_notification import build_notification

from pyhookkit.adapters.outbound.slack.text_renderer import SlackTextRenderer
from pyhookkit.entrypoints.slack_webhook_example import (
    run_slack_webhook_example,
)


def main() -> None:
    run_slack_webhook_example(build_notification(), SlackTextRenderer())


if __name__ == "__main__":
    main()
