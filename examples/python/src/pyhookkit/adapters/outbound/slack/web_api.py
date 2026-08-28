"""Authenticated Slack Web API transport and error handling."""

import random
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, cast

import httpx

from pyhookkit.adapters.outbound.slack.http_transport import SlackHttpTimeouts
from pyhookkit.adapters.outbound.slack.retry_policy import SlackRetryPolicy
from pyhookkit.json_types import JsonObject

_BOT_TOKEN = re.compile(r"^xoxb-[A-Za-z0-9-]+$")
_APP_TOKEN = re.compile(r"^xapp-[A-Za-z0-9-]+$")
_METHOD = re.compile(r"^[a-z][A-Za-z0-9.]+$")


class SlackWebApiErrorKind(StrEnum):
    """Stable Slack Web API error categories."""

    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMITED = "rate_limited"
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    TRANSIENT = "transient"
    TRANSPORT = "transport"
    MALFORMED_RESPONSE = "malformed_response"
    PERMANENT = "permanent"


class SlackWebApiError(RuntimeError):
    """A redacted Slack Web API failure."""

    def __init__(
        self,
        kind: SlackWebApiErrorKind,
        *,
        method: str,
        retryable: bool,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(f"Slack Web API {method} failed: {kind.value}")
        self.kind = kind
        self.method = method
        self.retryable = retryable
        self.status_code = status_code
        self.error_code = error_code


@dataclass(frozen=True, slots=True, repr=False)
class SlackBotToken:
    """A validated Slack bot token that never appears in representations."""

    value: str

    def __post_init__(self) -> None:
        if not _BOT_TOKEN.fullmatch(self.value):
            raise ValueError("invalid Slack bot token")

    def __repr__(self) -> str:
        return "SlackBotToken(value=<redacted>)"


@dataclass(frozen=True, slots=True, repr=False)
class SlackAppToken:
    """A validated Slack app token for Socket Mode."""

    value: str

    def __post_init__(self) -> None:
        if not _APP_TOKEN.fullmatch(self.value):
            raise ValueError("invalid Slack app token")

    def __repr__(self) -> str:
        return "SlackAppToken(value=<redacted>)"


class SlackWebApi(Protocol):
    """Call one authenticated Slack Web API method."""

    def call(
        self,
        method: str,
        payload: Mapping[str, object] | None = None,
    ) -> JsonObject: ...


class SlackWebApiClient:
    """Call Slack JSON methods with bounded retries and redacted failures."""

    def __init__(
        self,
        token: SlackBotToken | SlackAppToken,
        *,
        timeouts: SlackHttpTimeouts | None = None,
        retry_policy: SlackRetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
        post: Callable[..., httpx.Response] = httpx.post,
    ) -> None:
        self._token = token
        self._timeouts = timeouts or SlackHttpTimeouts()
        self._retry_policy = retry_policy or SlackRetryPolicy()
        self._sleep = sleep
        self._jitter = jitter
        self._post = post

    def call(
        self,
        method: str,
        payload: Mapping[str, object] | None = None,
    ) -> JsonObject:
        if not _METHOD.fullmatch(method):
            raise ValueError("invalid Slack Web API method")
        active_payload = {} if payload is None else dict(payload)
        for attempt in range(1, self._retry_policy.max_attempts + 1):
            try:
                response = self._post(
                    f"https://slack.com/api/{method}",
                    headers={"Authorization": f"Bearer {self._token.value}"},
                    json=active_payload,
                    timeout=httpx.Timeout(
                        connect=self._timeouts.connect_seconds,
                        read=self._timeouts.read_seconds,
                        write=self._timeouts.write_seconds,
                        pool=self._timeouts.pool_seconds,
                    ),
                )
            except (httpx.TimeoutException, httpx.TransportError):
                error = SlackWebApiError(
                    SlackWebApiErrorKind.TRANSPORT,
                    method=method,
                    retryable=True,
                )
                retry_after_seconds = None
            else:
                classification = _classify_response(method, response)
                error, result, retry_after_seconds = classification
                if result is not None:
                    return result
                if error is None:
                    raise RuntimeError("failed Slack response must contain an error")

            if not error.retryable or attempt == self._retry_policy.max_attempts:
                raise error
            self._sleep(
                self._retry_policy.delay(
                    completed_attempts=attempt,
                    retry_after_seconds=retry_after_seconds,
                    jitter=self._jitter(),
                )
            )
        raise RuntimeError("Slack Web API retry loop exhausted")


def _classify_response(
    method: str,
    response: httpx.Response,
) -> tuple[SlackWebApiError, None, float | None] | tuple[None, JsonObject, None]:
    if response.status_code == 429:
        return (
            SlackWebApiError(
                SlackWebApiErrorKind.RATE_LIMITED,
                method=method,
                retryable=True,
                status_code=429,
                error_code="ratelimited",
            ),
            None,
            _retry_after(response.headers),
        )
    if 500 <= response.status_code <= 599:
        return (
            SlackWebApiError(
                SlackWebApiErrorKind.TRANSIENT,
                method=method,
                retryable=True,
                status_code=response.status_code,
            ),
            None,
            None,
        )
    if response.status_code != 200:
        kind = (
            SlackWebApiErrorKind.AUTHENTICATION
            if response.status_code == 401
            else SlackWebApiErrorKind.PERMISSION
            if response.status_code == 403
            else SlackWebApiErrorKind.INVALID_REQUEST
        )
        return (
            SlackWebApiError(
                kind,
                method=method,
                retryable=False,
                status_code=response.status_code,
            ),
            None,
            None,
        )
    try:
        body: object = response.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        return (
            SlackWebApiError(
                SlackWebApiErrorKind.MALFORMED_RESPONSE,
                method=method,
                retryable=False,
                status_code=200,
            ),
            None,
            None,
        )
    mapping = cast(dict[object, object], body)
    if not all(isinstance(key, str) for key in mapping):
        return (
            SlackWebApiError(
                SlackWebApiErrorKind.MALFORMED_RESPONSE,
                method=method,
                retryable=False,
                status_code=200,
            ),
            None,
            None,
        )
    result = cast(JsonObject, mapping)
    if result.get("ok") is True:
        return None, result, None
    error_code = result.get("error")
    code = error_code if isinstance(error_code, str) else "unknown_error"
    kind = _ERROR_KINDS.get(code, SlackWebApiErrorKind.PERMANENT)
    return (
        SlackWebApiError(
            kind,
            method=method,
            retryable=kind
            in {
                SlackWebApiErrorKind.TRANSIENT,
                SlackWebApiErrorKind.RATE_LIMITED,
            },
            status_code=200,
            error_code=code,
        ),
        None,
        _retry_after(response.headers)
        if kind is SlackWebApiErrorKind.RATE_LIMITED
        else None,
    )


def _retry_after(headers: httpx.Headers) -> float | None:
    value = headers.get("Retry-After")
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


_ERROR_KINDS = {
    "invalid_auth": SlackWebApiErrorKind.AUTHENTICATION,
    "account_inactive": SlackWebApiErrorKind.AUTHENTICATION,
    "token_expired": SlackWebApiErrorKind.AUTHENTICATION,
    "token_revoked": SlackWebApiErrorKind.AUTHENTICATION,
    "not_authed": SlackWebApiErrorKind.AUTHENTICATION,
    "missing_scope": SlackWebApiErrorKind.PERMISSION,
    "no_permission": SlackWebApiErrorKind.PERMISSION,
    "not_in_channel": SlackWebApiErrorKind.PERMISSION,
    "channel_not_found": SlackWebApiErrorKind.NOT_FOUND,
    "user_not_found": SlackWebApiErrorKind.NOT_FOUND,
    "invalid_arguments": SlackWebApiErrorKind.INVALID_REQUEST,
    "invalid_arg_name": SlackWebApiErrorKind.INVALID_REQUEST,
    "invalid_array_arg": SlackWebApiErrorKind.INVALID_REQUEST,
    "request_timeout": SlackWebApiErrorKind.TRANSIENT,
    "ratelimited": SlackWebApiErrorKind.RATE_LIMITED,
    "fatal_error": SlackWebApiErrorKind.TRANSIENT,
    "internal_error": SlackWebApiErrorKind.TRANSIENT,
    "service_unavailable": SlackWebApiErrorKind.TRANSIENT,
}
