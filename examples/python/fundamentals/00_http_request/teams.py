"""Send Hello World to a Teams Workflow without pyhookkit."""

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Sequence
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import UUID

from example_message import MESSAGE

_WORKFLOW_URL_VARIABLE = "TEAMS_WORKFLOW_URL"
_WORKFLOW_CHANNEL_LINK_VARIABLE = "TEAMS_WORKFLOW_CHANNEL_LINK"
_LOGIC_APP_URL_VARIABLE = "TEAMS_LOGIC_APP_URL"
_LOGIC_APP_TEAM_VARIABLE = "TEAMS_LOGIC_APP_TEAM_ID"
_LOGIC_APP_CHANNEL_VARIABLE = "TEAMS_LOGIC_APP_CHANNEL_ID"
_TIMEOUT_SECONDS = 10.0


def build_card() -> dict[str, object]:
    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": MESSAGE,
                "wrap": True,
            }
        ],
    }


def build_payload() -> dict[str, object]:
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": build_card(),
            }
        ],
    }


def build_logic_app_payload(
    team_id: str,
    channel_id: str,
) -> dict[str, object]:
    return {
        "teamId": team_id,
        "channelId": channel_id,
        "eventId": "example-http-001",
        "card": build_card(),
    }


def build_workflow_payload(channel_link: str) -> dict[str, object]:
    team_id, channel_id = _channel_target(channel_link)
    return {
        **build_payload(),
        "channelLink": channel_link,
        "teamId": team_id,
        "channelId": channel_id,
    }


def send(
    url: str,
    payload: dict[str, object] | None = None,
) -> int:
    _require_https_url(url)
    active_payload = (
        build_workflow_payload(_required(_WORKFLOW_CHANNEL_LINK_VARIABLE, "--send"))
        if payload is None
        else payload
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(active_payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return response.status
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Teams Workflow returned HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("Teams Workflow request failed") from None


def main(arguments: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--send", action="store_true")
    action.add_argument("--send-logic-app", action="store_true")
    parsed = parser.parse_args(arguments)

    if not parsed.send and not parsed.send_logic_app:
        print(json.dumps(build_payload(), indent=2))
        return

    if parsed.send_logic_app:
        url = _required(_LOGIC_APP_URL_VARIABLE, "--send-logic-app")
        payload = build_logic_app_payload(
            _required(_LOGIC_APP_TEAM_VARIABLE, "--send-logic-app"),
            _required(_LOGIC_APP_CHANNEL_VARIABLE, "--send-logic-app"),
        )
    else:
        url = _required(_WORKFLOW_URL_VARIABLE, "--send")
        payload = build_workflow_payload(
            _required(_WORKFLOW_CHANNEL_LINK_VARIABLE, "--send")
        )
    status_code = send(url, payload)
    print(json.dumps({"state": "succeeded", "statusCode": status_code}, indent=2))


def _require_https_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Teams destination must be an HTTPS URL")


def _channel_target(channel_link: str) -> tuple[str, str]:
    parsed = urlsplit(channel_link)
    path_parts = parsed.path.split("/")
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "teams.microsoft.com"
        or parsed.fragment
        or len(path_parts) != 5
        or path_parts[1:3] != ["l", "channel"]
        or re.fullmatch(
            r"19:[A-Za-z0-9_-]+@thread\.(?:tacv2|skype)",
            unquote(path_parts[3]),
        )
        is None
        or not unquote(path_parts[4]).strip()
    ):
        raise ValueError("invalid Microsoft Teams channel link")
    query = parse_qs(parsed.query, strict_parsing=True)
    identifiers: dict[str, str] = {}
    for parameter in ("groupId", "tenantId"):
        values = query.get(parameter, [])
        if len(values) != 1:
            raise ValueError("invalid Microsoft Teams channel link")
        try:
            identifiers[parameter] = str(UUID(values[0]))
        except ValueError as error:
            raise ValueError("invalid Microsoft Teams channel link") from error
    return identifiers["groupId"], unquote(path_parts[3])


def _required(variable_name: str, option: str) -> str:
    value = os.environ.get(variable_name, "").strip()
    if not value:
        raise ValueError(f"{variable_name} is required with {option}")
    return value


if __name__ == "__main__":
    main()
