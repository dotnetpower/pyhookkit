"""Receive and acknowledge one Slack event over Socket Mode."""

import argparse
import asyncio
import json

from pyhookkit.adapters.inbound.slack.socket_mode import SlackSocketModeListener
from pyhookkit.entrypoints.slack_web_api import slack_socket_api_from_environment


async def _listen() -> None:
    event = await SlackSocketModeListener(
        slack_socket_api_from_environment()
    ).listen_once()
    print(
        json.dumps(
            {"eventId": event.event_id, "eventType": event.event_type},
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.listen_once:
        print(
            json.dumps(
                {
                    "transport": "Socket Mode",
                    "method": "apps.connections.open",
                    "acknowledgesEnvelope": True,
                    "live": False,
                },
                indent=2,
            )
        )
        return
    asyncio.run(_listen())


if __name__ == "__main__":
    main()
