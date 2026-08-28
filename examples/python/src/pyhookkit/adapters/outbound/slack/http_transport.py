"""HTTP transport for Slack webhook delivery."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import httpx

from pyhookkit.json_types import JsonObject


@dataclass(frozen=True, slots=True)
class SlackHttpTimeouts:
    """Explicit Slack connect, read, write, and pool timeouts."""

    connect_seconds: float = 5.0
    read_seconds: float = 10.0
    write_seconds: float = 10.0
    pool_seconds: float = 5.0

    def __post_init__(self) -> None:
        if (
            min(
                self.connect_seconds,
                self.read_seconds,
                self.write_seconds,
                self.pool_seconds,
            )
            <= 0
        ):
            raise ValueError("Slack HTTP timeouts must be positive")


@dataclass(frozen=True, slots=True)
class SlackHttpResponse:
    """HTTP fields needed for Slack response classification."""

    status_code: int
    headers: Mapping[str, str]
    body: str


class SlackTransportError(OSError):
    """A redacted Slack transport failure."""


class SlackHttpTransport(Protocol):
    """Send one Slack JSON payload."""

    def post(
        self,
        url: str,
        payload: JsonObject,
        timeouts: SlackHttpTimeouts,
    ) -> SlackHttpResponse:
        """POST JSON without exposing request details in errors."""
        ...


class HttpxSlackHttpTransport:
    """Send Slack webhook requests with explicit phase timeouts."""

    def post(
        self,
        url: str,
        payload: JsonObject,
        timeouts: SlackHttpTimeouts,
    ) -> SlackHttpResponse:
        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=httpx.Timeout(
                    connect=timeouts.connect_seconds,
                    read=timeouts.read_seconds,
                    write=timeouts.write_seconds,
                    pool=timeouts.pool_seconds,
                ),
            )
        except (httpx.TimeoutException, httpx.TransportError):
            raise SlackTransportError("Slack webhook transport failed") from None
        return SlackHttpResponse(
            status_code=response.status_code,
            headers=dict(response.headers.items()),
            body=response.text,
        )
