"""Render or send the explicit Teams Workflow thread fallback."""

from example_notification import build_notification

from pyhookkit.adapters.outbound.teams.message_renderer import TeamsMessageRenderer
from pyhookkit.entrypoints.teams_workflow_example import run_teams_workflow_example

_CAPABILITY_NOTICE = (
    "Teams Workflow webhooks cannot target a parent message. This fallback is "
    "delivered as a new channel message; use a bot or Microsoft Graph adapter "
    "when a true channel reply is required."
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
