"""Upload a synthetic report with Slack's current external upload flow."""

import argparse
import json

from pyhookkit.adapters.outbound.slack.file_upload import SlackFileUploader
from pyhookkit.entrypoints.slack_web_api import (
    required_slack_environment,
    slack_web_api_from_environment,
)

_REPORT = b"environment,status\nsynthetic,healthy\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true")
    arguments = parser.parse_args()
    if not arguments.upload:
        print(
            json.dumps(
                {
                    "methods": [
                        "files.getUploadURLExternal",
                        "HTTP binary upload",
                        "files.completeUploadExternal",
                    ],
                    "filename": "synthetic-status.csv",
                    "bytes": len(_REPORT),
                    "live": False,
                },
                indent=2,
            )
        )
        return

    reference = SlackFileUploader(slack_web_api_from_environment()).upload(
        filename="synthetic-status.csv",
        title="Synthetic status report",
        content=_REPORT,
        channel_id=required_slack_environment("SLACK_CHANNEL_ID"),
        initial_comment="Synthetic status report attached.",
    )
    print(
        json.dumps(
            {"state": "succeeded", "fileId": reference.identifier},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
