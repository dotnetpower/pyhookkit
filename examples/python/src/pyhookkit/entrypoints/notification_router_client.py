"""CLI client for canonical notification router submission."""

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from pyhookkit.adapters.inbound.canonical_notification_json import (
    load_canonical_notification,
)
from pyhookkit.adapters.outbound.canonical_notification_json import (
    canonical_notification_to_json,
)
from pyhookkit.adapters.outbound.router_client import (
    NotificationRouterClient,
    NotificationRouterToken,
    NotificationRouterUrl,
)


def run_notification_router_client(
    *,
    arguments: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Validate and submit one canonical notification file."""
    parser = argparse.ArgumentParser(
        description="Submit canonical JSON to the PyHookKit notification router.",
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--producer", required=True)
    parser.add_argument(
        "--url-env",
        default="NOTIFICATION_ROUTER_URL",
    )
    parser.add_argument(
        "--token-env",
        default="NOTIFICATION_ROUTER_TOKEN",
    )
    parsed = parser.parse_args(arguments)
    active_environment = os.environ if environment is None else environment
    raw_url = _required_environment(active_environment, parsed.url_env)
    raw_token = _required_environment(active_environment, parsed.token_env)
    notification = load_canonical_notification(parsed.input)
    result = NotificationRouterClient(
        NotificationRouterUrl(raw_url),
        NotificationRouterToken(raw_token),
        parsed.producer,
    ).submit(canonical_notification_to_json(notification))
    print(
        json.dumps(
            {
                "notificationId": result.notification_id,
                "duplicate": result.duplicate,
                "state": result.state,
            },
            indent=2,
        )
    )


def main() -> None:
    """Run with concise CLI errors."""
    try:
        run_notification_router_client()
    except ValueError as error:
        raise SystemExit(str(error)) from error


def _required_environment(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name, "").strip()
    if not value:
        raise ValueError(f"environment variable is required: {name}")
    return value


if __name__ == "__main__":
    main()
