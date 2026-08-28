"""Render or send the Hello World notification for Microsoft Teams."""

from example_notification import build_notification

from pyhookkit.adapters.outbound.teams.text_renderer import TeamsTextRenderer
from pyhookkit.entrypoints.teams_workflow_example import (
    run_teams_workflow_example,
)


def main() -> None:
    run_teams_workflow_example(build_notification(), TeamsTextRenderer())


if __name__ == "__main__":
    main()
