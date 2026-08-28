"""Render or send an image notification for Slack."""

import sys

from example_notification import ASSET_FILENAME, build_notification

from pyhookkit.adapters.outbound.slack.message_renderer import (
    SlackMessageRenderer,
)
from pyhookkit.entrypoints.example_asset import example_asset_url
from pyhookkit.entrypoints.slack_webhook_example import (
    run_slack_webhook_example,
)


def main() -> None:
    image_url = example_asset_url(ASSET_FILENAME) if "--send" in sys.argv[1:] else None
    notification = (
        build_notification() if image_url is None else build_notification(image_url)
    )
    run_slack_webhook_example(notification, SlackMessageRenderer())


if __name__ == "__main__":
    main()
