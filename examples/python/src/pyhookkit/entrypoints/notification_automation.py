"""Backward-compatible wrapper for the scenario CLI."""

from pyhookkit.entrypoints.scenario_cli import main, run_notification_automation

__all__ = ["main", "run_notification_automation"]


if __name__ == "__main__":
    main()
