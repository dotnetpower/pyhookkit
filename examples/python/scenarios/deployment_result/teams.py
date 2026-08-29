"""Render or send the deployment result for Microsoft Teams."""

from example_notification import build_notification

from pyhookkit.adapters.outbound.teams.message_renderer import TeamsMessageRenderer
from pyhookkit.entrypoints.example_asset import example_asset_marker
from pyhookkit.entrypoints.teams_workflow_example import run_teams_workflow_example


def main() -> None:
    renderer = TeamsMessageRenderer(
        hero_image_url=example_asset_marker("samples/scenarios/assets/deployment.png"),
        show_body_in_card=False,
        show_hero_label=False,
        hero_min_height=136,
    )
    run_teams_workflow_example(build_notification(), renderer)


if __name__ == "__main__":
    main()
