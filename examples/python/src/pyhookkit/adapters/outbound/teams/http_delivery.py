"""Shared HTTP response classification for Teams webhook destinations."""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from pyhookkit.adapters.outbound.teams.retry_policy import TeamsRetryPolicy
from pyhookkit.domain.delivery import (
    DeliveryError,
    DeliveryErrorKind,
    DeliveryResult,
    DeliveryState,
)
from pyhookkit.json_types import JsonObject


@dataclass(frozen=True, slots=True)
class TeamsHttpClassification:
    """A redacted Teams response classification with optional retry timing."""

    error: DeliveryError | None
    retry_after_seconds: float | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


def deliver_teams_http(
    url: str,
    payload: JsonObject,
    *,
    post: Callable[..., httpx.Response],
    timeout_seconds: float,
    retry_policy: TeamsRetryPolicy | None = None,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
) -> DeliveryResult:
    """POST one Teams payload with bounded retries and redacted results."""
    policy = retry_policy or TeamsRetryPolicy()
    for attempt in range(1, policy.max_attempts + 1):
        try:
            response = post(url, json=payload, timeout=timeout_seconds)
        except (httpx.TimeoutException, httpx.TransportError):
            classification = TeamsHttpClassification(
                DeliveryError(DeliveryErrorKind.TRANSPORT, retryable=True)
            )
        else:
            classification = classify_teams_response(response)
            if classification.succeeded:
                return DeliveryResult(DeliveryState.SUCCEEDED, attempts=attempt)

        error = classification.error
        if error is None:
            raise RuntimeError("failed Teams classification must contain an error")
        if not error.retryable or attempt == policy.max_attempts:
            return DeliveryResult(
                DeliveryState.FAILED,
                attempts=attempt,
                error=error,
            )
        sleep(
            policy.delay(
                completed_attempts=attempt,
                retry_after_seconds=classification.retry_after_seconds,
                jitter=jitter(),
            )
        )
    raise RuntimeError("Teams delivery loop exhausted without a result")


def classify_teams_response(response: httpx.Response) -> TeamsHttpClassification:
    """Classify one Teams response without retaining its body."""
    if 200 <= response.status_code <= 299:
        return TeamsHttpClassification(error=None)
    if response.status_code == 429:
        return TeamsHttpClassification(
            error=_error(
                DeliveryErrorKind.RATE_LIMITED,
                retryable=True,
                status_code=429,
            ),
            retry_after_seconds=_retry_after(response),
        )
    if 500 <= response.status_code <= 599:
        return TeamsHttpClassification(
            error=_error(
                DeliveryErrorKind.TRANSIENT_PROVIDER,
                retryable=True,
                status_code=response.status_code,
            )
        )
    kind = (
        DeliveryErrorKind.AUTHENTICATION
        if response.status_code == 401
        else DeliveryErrorKind.PERMISSION
        if response.status_code == 403
        else DeliveryErrorKind.INVALID_PAYLOAD
        if response.status_code == 400
        else DeliveryErrorKind.PERMANENT_PROVIDER
    )
    return TeamsHttpClassification(
        error=_error(kind, retryable=False, status_code=response.status_code)
    )


def _error(
    kind: DeliveryErrorKind,
    *,
    retryable: bool,
    status_code: int | None = None,
) -> DeliveryError:
    return DeliveryError(
        kind,
        retryable=retryable,
        status_code=status_code,
    )


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None
