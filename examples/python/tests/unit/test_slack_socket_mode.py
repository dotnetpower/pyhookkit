"""Slack Socket Mode listener tests."""

import asyncio
from collections.abc import Mapping
from contextlib import AbstractAsyncContextManager
from typing import Self, cast

import pytest

from pyhookkit.adapters.inbound.slack.socket_mode import (
    SlackSocketConnection,
    SlackSocketModeError,
    SlackSocketModeListener,
)
from pyhookkit.adapters.outbound.slack.web_api import SlackWebApi
from pyhookkit.json_types import JsonObject


class StubApi:
    def __init__(self, response: JsonObject) -> None:
        self.response = response

    def call(
        self,
        method: str,
        payload: Mapping[str, object] | None = None,
    ) -> JsonObject:
        assert method == "apps.connections.open"
        assert payload is None
        return self.response


class StubConnection(
    AbstractAsyncContextManager[SlackSocketConnection],
    SlackSocketConnection,
):
    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        self.sent: list[str | bytes] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> None:
        return None

    async def recv(self) -> str | bytes:
        return self.messages.pop(0)

    async def send(self, message: str | bytes) -> None:
        self.sent.append(message)


def test_listener_acknowledges_socket_envelope() -> None:
    connection = StubConnection(
        [
            '{"type": "hello", "connection_info": {"app_id": "A00000001"}}',
            """
            {
              "type": "events_api",
              "envelope_id": "En00000001",
              "payload": {
                "event_id": "Ev00000001",
                "event": {"type": "app_mention"}
              }
            }
            """,
        ]
    )
    listener = SlackSocketModeListener(
        cast(
            SlackWebApi,
            StubApi(
                {
                    "ok": True,
                    "url": "wss://wss-primary.slack.com/link/synthetic",
                }
            ),
        ),
        connector=lambda url: connection,
    )

    event = asyncio.run(listener.listen_once())

    assert event.event_type == "app_mention"
    assert connection.sent == ['{"envelope_id": "En00000001"}']


def test_listener_rejects_non_slack_socket_url() -> None:
    listener = SlackSocketModeListener(
        cast(
            SlackWebApi,
            StubApi({"ok": True, "url": "wss://malicious.example/link/synthetic"}),
        )
    )

    with pytest.raises(SlackSocketModeError, match="invalid"):
        asyncio.run(listener.listen_once())


def test_listener_rejects_disconnect_control_frame() -> None:
    connection = StubConnection(['{"type": "disconnect"}'])
    listener = SlackSocketModeListener(
        cast(
            SlackWebApi,
            StubApi(
                {
                    "ok": True,
                    "url": "wss://wss-primary.slack.com/link/synthetic",
                }
            ),
        ),
        connector=lambda url: connection,
    )

    with pytest.raises(SlackSocketModeError, match="reconnect"):
        asyncio.run(listener.listen_once())
