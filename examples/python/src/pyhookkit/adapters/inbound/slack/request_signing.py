"""Verify requests signed by Slack with replay protection."""

import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass


class SlackRequestVerificationError(PermissionError):
    """An inbound Slack request is unauthentic or stale."""


@dataclass(frozen=True, slots=True, repr=False)
class SlackSigningSecret:
    value: str

    def __post_init__(self) -> None:
        if len(self.value) < 8:
            raise ValueError("Slack signing secret must contain at least 8 characters")

    def __repr__(self) -> str:
        return "SlackSigningSecret(value=<redacted>)"


class SlackRequestVerifier:
    """Validate Slack v0 HMAC signatures and reject replayed requests."""

    def __init__(
        self,
        secret: SlackSigningSecret,
        *,
        maximum_age_seconds: int = 300,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if maximum_age_seconds < 1:
            raise ValueError("maximum Slack request age must be positive")
        self._secret = secret
        self._maximum_age_seconds = maximum_age_seconds
        self._clock = clock

    def verify(self, timestamp: str, signature: str, body: bytes) -> None:
        try:
            request_time = int(timestamp)
        except ValueError:
            raise SlackRequestVerificationError(
                "Slack request timestamp is invalid"
            ) from None
        if abs(self._clock() - request_time) > self._maximum_age_seconds:
            raise SlackRequestVerificationError("Slack request timestamp is stale")
        base = b"v0:" + timestamp.encode() + b":" + body
        digest = hmac.new(
            self._secret.value.encode(),
            base,
            hashlib.sha256,
        ).hexdigest()
        expected = f"v0={digest}"
        if not hmac.compare_digest(expected, signature):
            raise SlackRequestVerificationError("Slack request signature is invalid")
