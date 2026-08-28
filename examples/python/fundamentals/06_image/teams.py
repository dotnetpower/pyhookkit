"""Render or send the image example for Microsoft Teams."""

import sys

from example_notification import ASSET_FILENAME, build_notification

from pyhookkit.adapters.outbound.teams.message_renderer import TeamsMessageRenderer
from pyhookkit.entrypoints.example_asset import (
    example_asset_marker,
    example_asset_url,
)
from pyhookkit.entrypoints.teams_workflow_example import run_teams_workflow_example


def main() -> None:
    image_url = example_asset_url(ASSET_FILENAME) if "--send" in sys.argv[1:] else None
    notification = (
        build_notification() if image_url is None else build_notification(image_url)
    )
    renderer = TeamsMessageRenderer(
        hero_image_url=example_asset_marker(
            "samples/standard-video/assets/video_image.png"
        )
    )
    run_teams_workflow_example(notification, renderer)


if __name__ == "__main__":
    main()
