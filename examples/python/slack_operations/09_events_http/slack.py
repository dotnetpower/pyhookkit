"""Run a minimal signed Slack Events API HTTP endpoint."""

import argparse
import json
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pyhookkit.adapters.inbound.slack.events import SlackEventsHttpHandler
from pyhookkit.adapters.inbound.slack.request_signing import (
    SlackRequestVerificationError,
    SlackRequestVerifier,
    SlackSigningSecret,
)
from pyhookkit.entrypoints.slack_web_api import required_slack_environment


def _handler_type(
    events: SlackEventsHttpHandler,
) -> type[BaseHTTPRequestHandler]:
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
                acknowledgment = events.handle(headers, body)
            except (SlackRequestVerificationError, ValueError):
                self.send_error(401)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(acknowledgment.body)
            if acknowledgment.event is not None:
                print(
                    json.dumps(
                        {
                            "eventId": acknowledgment.event.event_id,
                            "eventType": acknowledgment.event.event_type,
                        }
                    )
                )

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=3000)
    arguments = parser.parse_args()
    if not arguments.serve:
        print(
            json.dumps(
                {
                    "transport": "Events API HTTP",
                    "path": "/",
                    "port": arguments.port,
                    "signatureVerification": True,
                    "live": False,
                },
                indent=2,
            )
        )
        return

    secret = SlackSigningSecret(required_slack_environment("SLACK_SIGNING_SECRET"))
    events = SlackEventsHttpHandler(SlackRequestVerifier(secret))
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), _handler_type(events))
    print(f"Slack Events API endpoint listening on 127.0.0.1:{arguments.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
