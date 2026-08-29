"""Render or deliver the Microsoft Teams retry example."""

from example_notification import build_notification

from pyhookkit.adapters.outbound.teams.message_renderer import TeamsMessageRenderer
from pyhookkit.entrypoints.teams_workflow_example import run_teams_workflow_example


def main() -> None:
    run_teams_workflow_example(
        build_notification(),
        TeamsMessageRenderer(hero_image_url=None),
    )


if __name__ == "__main__":
    main()
