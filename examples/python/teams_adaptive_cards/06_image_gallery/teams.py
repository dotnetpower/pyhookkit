"""Render or send the licensed image gallery Adaptive Card."""

from pathlib import Path

from pyhookkit.entrypoints.teams_card_example import run_teams_card_file_example


def main() -> None:
    run_teams_card_file_example(Path(__file__).with_name("card.json"))


if __name__ == "__main__":
    main()
