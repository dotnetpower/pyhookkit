"""Render or send logical mentions for Microsoft Teams."""

import os
import sys

from example_notification import build_notification

from pyhookkit.adapters.outbound.teams.identity import (
    TeamsIdentity,
    TeamsIdentityDirectory,
    TeamsIdentityNotFoundError,
)
from pyhookkit.adapters.outbound.teams.message_renderer import (
    TeamsGroupMentionPolicy,
    TeamsMessageRenderer,
)
from pyhookkit.entrypoints.teams_workflow_example import run_teams_workflow_example


def main() -> None:
    display_name = _identity("TEAMS_TEST_USER_NAME", "Example Owner")
    if any(character in display_name for character in "<>&"):
        raise ValueError(
            "TEAMS_TEST_USER_NAME must not contain Teams markup characters"
        )
    identities = TeamsIdentityDirectory(
        {
            "example-owner": TeamsIdentity(
                _identity("TEAMS_TEST_USER_ID", "example-owner@pyhookkit.example"),
                display_name,
            )
        }
    )
    run_teams_workflow_example(
        build_notification(),
        TeamsMessageRenderer(
            identities,
            hero_image_url=None,
            group_mention_policy=TeamsGroupMentionPolicy.OMIT,
        ),
    )


def _identity(variable_name: str, synthetic_value: str) -> str:
    sending = any(option in sys.argv[1:] for option in ("--send", "--send-logic-app"))
    if not sending:
        return synthetic_value
    value = os.environ.get(variable_name, "").strip()
    if value:
        return value
    raise TeamsIdentityNotFoundError(
        f"{variable_name} is required when sending the mention example"
    )


if __name__ == "__main__":
    main()
