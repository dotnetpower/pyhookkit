"""Receive and acknowledge one Slack Socket Mode envelope."""

import json
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol, cast
from urllib.parse import urlsplit

from websockets.asyncio.client import connect

from pyhookkit.adapters.outbound.slack.web_api import SlackWebApi


class SlackSocketModeError(RuntimeError):
    """A redacted Slack Socket Mode protocol failure."""


@dataclass(frozen=True, slots=True)
class SlackSocketEvent:
    envelope_id: str
    event_id: str
    event_type: str


class SlackSocketConnection(Protocol):
    async def recv(self) -> str | bytes: ...

    async def send(self, message: str | bytes) -> None: ...


class SlackSocketConnector(Protocol):
    def __call__(
        self,
        url: str,
    ) -> AbstractAsyncContextManager[SlackSocketConnection]: ...


def _connect(url: str) -> AbstractAsyncContextManager[SlackSocketConnection]:
    connection = connect(url)
    return cast(AbstractAsyncContextManager[SlackSocketConnection], connection)


class SlackSocketModeListener:
    """Open a short-lived Socket Mode URL and acknowledge envelopes."""

    def __init__(
        self,
        api: SlackWebApi,
        *,
        connector: SlackSocketConnector = _connect,
    ) -> None:
        self._api = api
        self._connector = connector

    async def listen_once(self) -> SlackSocketEvent:
        response = self._api.call("apps.connections.open")
        url = response.get("url")
        if not isinstance(url, str):
            raise SlackSocketModeError(
                "Slack apps.connections.open response requires a URL"
            )
        _validate_socket_url(url)
        async with self._connector(url) as connection:
            while True:
                raw_envelope = await connection.recv()
                envelope = _parse_envelope(raw_envelope)
                if envelope is None:
                    continue
                await connection.send(json.dumps({"envelope_id": envelope.envelope_id}))
                return envelope


def _validate_socket_url(url: str) -> None:
    parsed = urlsplit(url)
    hostname = parsed.hostname
    if (
        parsed.scheme != "wss"
        or hostname is None
        or not (hostname == "slack.com" or hostname.endswith(".slack.com"))
    ):
        raise SlackSocketModeError("Slack returned an invalid Socket Mode URL")


def _parse_envelope(raw: str | bytes) -> SlackSocketEvent | None:
    try:
        value: object = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SlackSocketModeError("Slack Socket Mode envelope must be JSON") from None
    if not isinstance(value, dict):
        raise SlackSocketModeError("Slack Socket Mode envelope must be an object")
    mapping = cast(dict[object, object], value)
    envelope_type = mapping.get("type")
    if envelope_type == "hello":
        return None
    if envelope_type == "disconnect":
        raise SlackSocketModeError("Slack requested a Socket Mode reconnect")
    if envelope_type != "events_api":
        raise SlackSocketModeError("unsupported Slack Socket Mode envelope")
    envelope_id = _required_string(mapping, "envelope_id")
    payload = mapping.get("payload")
    if not isinstance(payload, dict):
        raise SlackSocketModeError("Slack Socket Mode envelope requires payload")
    payload_mapping = cast(dict[object, object], payload)
    event_id = _required_string(payload_mapping, "event_id")
    event_value = payload_mapping.get("event")
    if not isinstance(event_value, dict):
        raise SlackSocketModeError("Slack Socket Mode payload requires event")
    event = cast(dict[object, object], event_value)
    return SlackSocketEvent(
        envelope_id=envelope_id,
        event_id=event_id,
        event_type=_required_string(event, "type"),
    )


def _required_string(value: dict[object, object], key: str) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate:
        raise SlackSocketModeError(f"Slack Socket Mode envelope requires {key}")
    return candidate
