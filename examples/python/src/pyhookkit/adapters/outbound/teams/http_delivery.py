"""Shared HTTP response classification for Teams webhook destinations."""

from collections.abc import Callable

import httpx

from pyhookkit.domain.delivery import (
    DeliveryError,
    DeliveryErrorKind,
    DeliveryResult,
    DeliveryState,
)
from pyhookkit.json_types import JsonObject


def deliver_teams_http(
    url: str,
    payload: JsonObject,
    *,
    post: Callable[..., httpx.Response],
    timeout_seconds: float,
) -> DeliveryResult:
    """POST one Teams payload and return a redacted provider-neutral result."""
    try:
        response = post(url, json=payload, timeout=timeout_seconds)
    except (httpx.TimeoutException, httpx.TransportError):
        return _failure(DeliveryErrorKind.TRANSPORT, retryable=True)
    if 200 <= response.status_code <= 299:
        return DeliveryResult(DeliveryState.SUCCEEDED, attempts=1)
    if response.status_code == 429:
        return _failure(
            DeliveryErrorKind.RATE_LIMITED,
            retryable=True,
            status_code=429,
        )
    if 500 <= response.status_code <= 599:
        return _failure(
            DeliveryErrorKind.TRANSIENT_PROVIDER,
            retryable=True,
            status_code=response.status_code,
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
    return _failure(kind, retryable=False, status_code=response.status_code)


def _failure(
    kind: DeliveryErrorKind,
    *,
    retryable: bool,
    status_code: int | None = None,
) -> DeliveryResult:
    return DeliveryResult(
        DeliveryState.FAILED,
        attempts=1,
        error=DeliveryError(
            kind,
            retryable=retryable,
            status_code=status_code,
        ),
    )
