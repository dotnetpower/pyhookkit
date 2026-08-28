"""Render or send the progress timeline Adaptive Card."""

from pathlib import Path

from pyhookkit.entrypoints.teams_card_example import run_teams_card_file_example

if __name__ == "__main__":
    run_teams_card_file_example(Path(__file__).with_name("card.json"))
