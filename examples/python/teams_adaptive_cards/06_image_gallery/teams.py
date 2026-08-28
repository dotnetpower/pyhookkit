"""Render or send the licensed image gallery Adaptive Card."""

import sys
from pathlib import Path

from pyhookkit.entrypoints.teams_card_assets import teams_asset_replacements
from pyhookkit.entrypoints.teams_card_example import run_teams_card_file_example

_ASSETS = (
    "adaptive-card-cat-hero.png",
    "adaptive-card-cat-glasses.png",
    "adaptive-card-cat-portrait.png",
)


def main() -> None:
    replacements = (
        teams_asset_replacements(_ASSETS) if "--send" in sys.argv[1:] else None
    )
    run_teams_card_file_example(
        Path(__file__).with_name("card.json"),
        replacements=replacements,
    )


if __name__ == "__main__":
    main()
