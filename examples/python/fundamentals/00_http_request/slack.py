"""Send Hello World to a Slack Incoming Webhook without pyhookkit."""

import argparse
import json
import os
import urllib.error
import urllib.request
from collections.abc import Sequence
from urllib.parse import urlsplit

from example_message import MESSAGE

_ENVIRONMENT_VARIABLE = "SLACK_WEBHOOK_URL"
_TIMEOUT_SECONDS = 10.0


def build_payload() -> dict[str, object]:
    return {"text": MESSAGE}


def send(webhook_url: str) -> int:
    _require_https_url(webhook_url)
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(build_payload()).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return response.status
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Slack returned HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("Slack webhook request failed") from None


def main(arguments: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true")
    parsed = parser.parse_args(arguments)

    if not parsed.send:
        print(json.dumps(build_payload(), indent=2))
        return

    webhook_url = os.environ.get(_ENVIRONMENT_VARIABLE, "").strip()
    if not webhook_url:
        raise ValueError(f"{_ENVIRONMENT_VARIABLE} is required with --send")
    status_code = send(webhook_url)
    print(json.dumps({"state": "succeeded", "statusCode": status_code}, indent=2))


def _require_https_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{_ENVIRONMENT_VARIABLE} must be an HTTPS URL")


if __name__ == "__main__":
    main()
