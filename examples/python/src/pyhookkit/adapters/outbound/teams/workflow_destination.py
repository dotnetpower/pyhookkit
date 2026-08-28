"""Microsoft Teams Workflow delivery."""

from collections.abc import Callable

import httpx

from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.domain.delivery import (
    DeliveryError,
    DeliveryErrorKind,
    DeliveryResult,
    DeliveryState,
)
from pyhookkit.json_types import JsonObject


class TeamsWorkflowDestination:
    """Deliver one Adaptive Card envelope to a Teams Workflow."""

    def __init__(
        self,
        workflow_url: TeamsWorkflowUrl,
        *,
        post: Callable[..., httpx.Response] = httpx.post,
        timeout_seconds: float = 15.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Teams Workflow timeout must be positive")
        self._workflow_url = workflow_url
        self._post = post
        self._timeout_seconds = timeout_seconds

    def send(self, payload: JsonObject) -> DeliveryResult:
        try:
            response = self._post(
                self._workflow_url.value,
                json=payload,
                timeout=self._timeout_seconds,
            )
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
