"""Render or send the user mention Adaptive Card."""

import os
import sys
from pathlib import Path

from pyhookkit.entrypoints.teams_card_example import (
    TeamsCardExampleError,
    run_teams_card_file_example,
)

_USER_ID_MARKER = "{{TEAMS_TEST_USER_ID}}"
_USER_NAME_MARKER = "{{TEAMS_TEST_USER_NAME}}"


def main() -> None:
    replacements: dict[str, str] | None = None
    sending = any(option in sys.argv[1:] for option in ("--send", "--send-logic-app"))
    if sending:
        user_id = os.environ.get("TEAMS_TEST_USER_ID", "").strip()
        user_name = os.environ.get("TEAMS_TEST_USER_NAME", "").strip()
        if not user_id or not user_name:
            raise TeamsCardExampleError(
                "TEAMS_TEST_USER_ID and TEAMS_TEST_USER_NAME are required when sending"
            )
        if any(character in user_name for character in "<>&"):
            raise TeamsCardExampleError(
                "TEAMS_TEST_USER_NAME must not contain Teams markup characters"
            )
        replacements = {
            _USER_ID_MARKER: user_id,
            _USER_NAME_MARKER: user_name,
        }
    run_teams_card_file_example(
        Path(__file__).with_name("card.json"),
        replacements=replacements,
    )


if __name__ == "__main__":
    main()
