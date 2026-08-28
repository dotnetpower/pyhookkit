"""Render or send the deployment result for Slack."""

from example_notification import build_notification

from pyhookkit.adapters.outbound.slack.message_renderer import SlackMessageRenderer
from pyhookkit.entrypoints.slack_webhook_example import run_slack_webhook_example


def main() -> None:
    run_slack_webhook_example(build_notification(), SlackMessageRenderer())


if __name__ == "__main__":
    main()
