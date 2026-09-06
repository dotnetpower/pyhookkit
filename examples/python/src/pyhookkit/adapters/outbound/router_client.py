"""Authenticated client for submitting canonical notifications to a router."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast
from urllib.parse import urlsplit

import httpx

from pyhookkit.json_types import JsonObject

_TARGET_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True, repr=False)
class NotificationRouterUrl:
    """Validated central router base URL."""

    value: str

    def __post_init__(self) -> None:
        parsed = urlsplit(self.value)
        loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if (
            parsed.scheme not in ({"http"} if loopback else {"https"})
            or parsed.hostname is None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "notification router URL must use HTTPS, except on loopback"
            )

    @property
    def submission_url(self) -> str:
        """Return the canonical submission endpoint."""
        return f"{self.value.rstrip('/')}/v1/notifications"

    def target_submission_url(self, target_id: str) -> str:
        """Return one validated destination-specific submission endpoint."""
        if _TARGET_ID.fullmatch(target_id) is None:
            raise ValueError("notification router target ID must use kebab-case")
        return f"{self.value.rstrip('/')}/v1/destinations/{target_id}/notifications"

    def __repr__(self) -> str:
        return "NotificationRouterUrl(value=<redacted>)"


@dataclass(frozen=True, slots=True, repr=False)
class NotificationRouterToken:
    """Producer bearer credential."""

    value: str

    def __post_init__(self) -> None:
        if len(self.value) < 16:
            raise ValueError("notification router token must contain 16 characters")

    def __repr__(self) -> str:
        return "NotificationRouterToken(value=<redacted>)"


@dataclass(frozen=True, slots=True)
class RouterSubmissionResult:
    """Redacted result returned for an accepted notification."""

    notification_id: str
    duplicate: bool
    state: str


class NotificationRouterClient:
    """Submit strict canonical JSON using producer-isolated credentials."""

    def __init__(
        self,
        url: NotificationRouterUrl,
        token: NotificationRouterToken,
        producer: str,
        *,
        post: Callable[..., httpx.Response] = httpx.post,
        timeout_seconds: float = 15.0,
    ) -> None:
        if not producer.strip():
            raise ValueError("notification router producer must not be blank")
        if timeout_seconds <= 0:
            raise ValueError("notification router timeout must be positive")
        self._url = url
        self._token = token
        self._producer = producer
        self._post = post
        self._timeout_seconds = timeout_seconds

    def submit(
        self,
        payload: JsonObject,
        *,
        target_id: str | None = None,
    ) -> RouterSubmissionResult:
        """Submit a canonical notification without retaining provider output."""
        response = self._post(
            (
                self._url.submission_url
                if target_id is None
                else self._url.target_submission_url(target_id)
            ),
            json=payload,
            headers={
                "Authorization": f"Bearer {self._token.value}",
                "X-PyHookKit-Producer": self._producer,
            },
            timeout=self._timeout_seconds,
        )
        if response.status_code != 202:
            raise ValueError(
                f"notification router rejected request with HTTP {response.status_code}"
            )
        value: object = response.json()
        if not isinstance(value, dict):
            raise ValueError("notification router response must be a JSON object")
        mapping = cast(dict[object, object], value)
        notification_id = mapping.get("notificationId")
        duplicate = mapping.get("duplicate")
        state = mapping.get("state")
        if (
            not isinstance(notification_id, str)
            or not isinstance(duplicate, bool)
            or not isinstance(state, str)
        ):
            raise ValueError("notification router response is missing required fields")
        return RouterSubmissionResult(notification_id, duplicate, state)
