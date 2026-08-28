"""Render or send the hero image Adaptive Card."""

import sys
from pathlib import Path

from pyhookkit.entrypoints.teams_card_assets import teams_asset_replacements
from pyhookkit.entrypoints.teams_card_example import run_teams_card_file_example

_ASSET = "samples/editorial/assets/editorialHero.png"


def main() -> None:
    replacements = (
        teams_asset_replacements((_ASSET,)) if "--send" in sys.argv[1:] else None
    )
    run_teams_card_file_example(
        Path(__file__).with_name("card.json"),
        replacements=replacements,
    )


if __name__ == "__main__":
    main()
