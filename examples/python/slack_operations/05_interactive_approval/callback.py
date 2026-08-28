"""A minimal signed Slack approval callback endpoint."""

import argparse
import json
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pyhookkit.adapters.inbound.slack.approval_interaction import (
    parse_slack_approval,
)
from pyhookkit.adapters.inbound.slack.request_signing import (
    SlackRequestVerificationError,
    SlackRequestVerifier,
    SlackSigningSecret,
)
from pyhookkit.entrypoints.slack_web_api import required_slack_environment


def _handler_type(verifier: SlackRequestVerifier) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400)
                return
            body = self.rfile.read(content_length)
            headers: Mapping[str, str] = dict(self.headers.items())
            try:
                verifier.verify(
                    headers.get("X-Slack-Request-Timestamp", ""),
                    headers.get("X-Slack-Signature", ""),
                    body,
                )
                interaction = parse_slack_approval(body)
            except (SlackRequestVerificationError, ValueError):
                self.send_error(401)
                return
            self.send_response(200)
            self.end_headers()
            print(
                json.dumps(
                    {
                        "decision": interaction.decision,
                        "eventId": interaction.event_id,
                        "userId": interaction.user_id,
                    }
                )
            )

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=3001)
    arguments = parser.parse_args()
    if not arguments.serve:
        print(
            json.dumps(
                {
                    "transport": "Slack interactivity HTTP",
                    "signatureVerification": True,
                    "port": arguments.port,
                    "live": False,
                },
                indent=2,
            )
        )
        return
    secret = SlackSigningSecret(required_slack_environment("SLACK_SIGNING_SECRET"))
    verifier = SlackRequestVerifier(secret)
    server = ThreadingHTTPServer(
        ("127.0.0.1", arguments.port),
        _handler_type(verifier),
    )
    print(f"Slack interaction endpoint listening on 127.0.0.1:{arguments.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
