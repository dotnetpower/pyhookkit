"""Render the explicit Teams Workflow mutation limitation."""

from example_notification import build_notification

from pyhookkit.adapters.outbound.teams.message_renderer import TeamsMessageRenderer
from pyhookkit.entrypoints.teams_workflow_example import run_teams_workflow_example

_CAPABILITY_NOTICE = (
    "Teams Workflow webhooks cannot update or delete an existing channel "
    "message. Sending this example creates a new limitation notice; use a bot "
    "or Microsoft Graph adapter for message mutation."
)


def main() -> None:
    run_teams_workflow_example(
        build_notification(),
        TeamsMessageRenderer(
            hero_image_url=None,
            capability_notice=_CAPABILITY_NOTICE,
        ),
    )


if __name__ == "__main__":
    main()
