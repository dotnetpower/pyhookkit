#!/usr/bin/env python3
"""Write an access-scoped Microsoft Teams channel inventory from Graph."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import cast
from uuid import UUID

type JsonValue = (
    bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None
)
type Transport = Callable[[urllib.request.Request], tuple[int, bytes]]

GRAPH_ORIGIN = "https://graph.microsoft.com"


class ChannelInventoryError(RuntimeError):
    """Raised when a safe channel inventory cannot be produced."""


class GraphChannelDirectory:
    """Read only the basic channel properties needed for routing validation."""

    def __init__(
        self, access_token: str, *, transport: Transport | None = None
    ) -> None:
        if not access_token:
            raise ChannelInventoryError(
                "Microsoft Graph access token must not be blank"
            )
        self._access_token = access_token
        self._transport = transport or _send

    def channels(
        self, team_id: UUID, *, include_incoming: bool
    ) -> list[dict[str, JsonValue]]:
        collection = "allChannels" if include_incoming else "channels"
        select = urllib.parse.quote("id,displayName,membershipType", safe=",")
        next_url: str | None = (
            f"{GRAPH_ORIGIN}/v1.0/teams/{team_id}/{collection}?$select={select}"
        )
        channels: list[dict[str, JsonValue]] = []
        while next_url is not None:
            self._validate_graph_url(next_url)
            page = self._get(next_url)
            values = page.get("value")
            if not isinstance(values, list) or any(
                not isinstance(item, dict) for item in values
            ):
                raise ChannelInventoryError("Graph channel response is malformed")
            for item in cast(list[dict[str, JsonValue]], values):
                channels.append(_channel_summary(item))
            raw_next_url = page.get("@odata.nextLink")
            if raw_next_url is not None and not isinstance(raw_next_url, str):
                raise ChannelInventoryError("Graph next link is malformed")
            next_url = raw_next_url
        return channels

    def _get(self, url: str) -> dict[str, JsonValue]:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
            },
        )
        status, body = self._transport(request)
        if status != 200:
            raise ChannelInventoryError(
                f"Microsoft Graph GET failed with HTTP {status}"
            )
        decoded = cast(JsonValue, json.loads(body))
        if not isinstance(decoded, dict):
            raise ChannelInventoryError("Graph response must be a JSON object")
        return decoded

    @staticmethod
    def _validate_graph_url(url: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "graph.microsoft.com":
            raise ChannelInventoryError("Graph next link has an unexpected origin")


def _channel_summary(channel: dict[str, JsonValue]) -> dict[str, JsonValue]:
    channel_id = channel.get("id")
    display_name = channel.get("displayName")
    membership_type = channel.get("membershipType")
    if not all(isinstance(value, str) for value in (channel_id, display_name)):
        raise ChannelInventoryError("Graph channel is missing an ID or display name")
    if membership_type is not None and not isinstance(membership_type, str):
        raise ChannelInventoryError("Graph channel membership type is malformed")
    return {
        "id": channel_id,
        "displayName": display_name,
        "membershipType": membership_type,
    }


def _send(request: urllib.request.Request) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        error.read()
        return error.code, b""
    except urllib.error.URLError as error:
        raise ChannelInventoryError("Microsoft Graph request failed") from error


def write_private_report(path: Path, report: dict[str, JsonValue]) -> None:
    """Create or replace a report with owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        json.dump(report, destination, indent=2)
        destination.write("\n")
    path.chmod(0o600)


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("team ID must be a GUID") from error


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team-id", type=_uuid, required=True)
    parser.add_argument("--include-incoming", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--token-env", default="MICROSOFT_GRAPH_ACCESS_TOKEN")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    directory = GraphChannelDirectory(os.environ.get(args.token_env, ""))
    channels = directory.channels(args.team_id, include_incoming=args.include_incoming)
    report: dict[str, JsonValue] = {
        "teamId": str(args.team_id),
        "scope": "owned-and-incoming" if args.include_incoming else "owned",
        "channels": cast(list[JsonValue], channels),
    }
    write_private_report(args.output, report)
    counts = Counter(
        cast(str, channel.get("membershipType") or "unknown") for channel in channels
    )
    summary = ", ".join(f"{key}={counts[key]}" for key in sorted(counts))
    print(f"Channel access verified: total={len(channels)}; {summary}")
    print(f"Private report written: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except ChannelInventoryError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
