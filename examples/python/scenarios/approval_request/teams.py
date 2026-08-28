"""Render or send the approval request for Microsoft Teams."""

from example_notification import build_notification

from pyhookkit.adapters.outbound.teams.identity import (
    TeamsIdentity,
    TeamsIdentityDirectory,
)
from pyhookkit.adapters.outbound.teams.message_renderer import TeamsMessageRenderer
from pyhookkit.entrypoints.teams_workflow_example import run_teams_workflow_example


def main() -> None:
    identities = TeamsIdentityDirectory(
        {
            "example-approver": TeamsIdentity(
                "example-approver@pyhookkit.example",
                "Example Approver",
            )
        }
    )
    run_teams_workflow_example(
        build_notification(),
        TeamsMessageRenderer(identities),
    )


if __name__ == "__main__":
    main()
