"""Send Hello World to a Teams Workflow without pyhookkit."""

import argparse
import json
import os
import urllib.error
import urllib.request
from collections.abc import Sequence
from urllib.parse import urlsplit

from example_message import MESSAGE

_ENVIRONMENT_VARIABLE = "TEAMS_WORKFLOW_URL"
_TIMEOUT_SECONDS = 10.0


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
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": MESSAGE,
                            "wrap": True,
                        }
                    ],
                },
            }
        ],
    }


def send(workflow_url: str) -> int:
    _require_https_url(workflow_url)
    request = urllib.request.Request(
        workflow_url,
        data=json.dumps(build_payload()).encode(),
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
    parser.add_argument("--send", action="store_true")
    parsed = parser.parse_args(arguments)

    if not parsed.send:
        print(json.dumps(build_payload(), indent=2))
        return

    workflow_url = os.environ.get(_ENVIRONMENT_VARIABLE, "").strip()
    if not workflow_url:
        raise ValueError(f"{_ENVIRONMENT_VARIABLE} is required with --send")
    status_code = send(workflow_url)
    print(json.dumps({"state": "succeeded", "statusCode": status_code}, indent=2))


def _require_https_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{_ENVIRONMENT_VARIABLE} must be an HTTPS URL")


if __name__ == "__main__":
    main()
