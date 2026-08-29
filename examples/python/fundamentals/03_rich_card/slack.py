"""Render or send the rich card for Slack."""

from example_notification import build_notification

from pyhookkit.adapters.outbound.slack.message_renderer import (
    SlackMessageRenderer,
)
from pyhookkit.entrypoints.example_asset import example_asset_marker
from pyhookkit.entrypoints.slack_webhook_example import (
    run_slack_webhook_example,
)


def main() -> None:
    renderer = SlackMessageRenderer(
        hero_image_url=example_asset_marker("samples/cafe-menu/assets/hero.png")
    )
    run_slack_webhook_example(build_notification(), renderer)


if __name__ == "__main__":
    main()
