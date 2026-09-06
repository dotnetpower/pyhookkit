"""Send Hello World to a Teams Workflow without pyhookkit."""

import argparse
import json
import os
import re
import urllib.request
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import UUID

from example_message import MESSAGE

_ALLOWED_TEAMS_HOSTS = frozenset({"teams.cloud.microsoft", "teams.microsoft.com"})
_CHANNEL_LINK_ERROR = (
    "TEAMS_WORKFLOW_CHANNEL_LINK must be a complete Microsoft Teams Copy link"
)


def build_payload() -> dict[str, object]:
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [{"type": "TextBlock", "text": MESSAGE, "wrap": True}],
                },
            }
        ],
    }


def build_workflow_payload(channel_link: str) -> dict[str, object]:
    team_id, channel_id = _channel_target(channel_link)
    return {
        **build_payload(),
        "teamId": team_id,
        "channelId": channel_id,
    }


def send(url: str) -> int:
    parsed_url = urlsplit(url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("Teams destination must be an HTTPS URL")

    channel_link = os.environ.get("TEAMS_WORKFLOW_CHANNEL_LINK", "").strip()
    if not channel_link:
        raise ValueError("TEAMS_WORKFLOW_CHANNEL_LINK is required with --send")

    request = urllib.request.Request(
        url,
        data=json.dumps(build_workflow_payload(channel_link)).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10.0) as response:
        return response.status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true")
    if not parser.parse_args().send:
        print(json.dumps(build_payload(), indent=2))
        return

    workflow_url = os.environ.get("TEAMS_WORKFLOW_URL", "").strip()
    if not workflow_url:
        raise ValueError("TEAMS_WORKFLOW_URL is required with --send")

    status_code = send(workflow_url)
    print(json.dumps({"state": "succeeded", "statusCode": status_code}, indent=2))


def _channel_target(channel_link: str) -> tuple[str, str]:
    parsed = urlsplit(channel_link)
    try:
        channel = re.fullmatch(
            r"/l/channel/(19:[A-Za-z0-9_-]+@thread\.(?:tacv2|skype))/[^/]+",
            unquote(parsed.path),
        )
        query = parse_qs(parsed.query, strict_parsing=True)
        group_ids = query["groupId"]
        if (
            parsed.scheme != "https"
            or parsed.hostname not in _ALLOWED_TEAMS_HOSTS
            or parsed.port not in {None, 443}
            or parsed.fragment
            or channel is None
            or len(group_ids) != 1
        ):
            raise ValueError
        return str(UUID(group_ids[0])), channel.group(1)
    except (KeyError, ValueError) as error:
        raise ValueError(_CHANNEL_LINK_ERROR) from error


if __name__ == "__main__":
    main()
