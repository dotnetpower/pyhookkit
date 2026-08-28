"""Reliable Slack Incoming Webhook delivery."""

import random
import time
from collections.abc import Callable

from pyhookkit.adapters.outbound.slack.http_transport import (
    HttpxSlackHttpTransport,
    SlackHttpTimeouts,
    SlackHttpTransport,
    SlackTransportError,
)
from pyhookkit.adapters.outbound.slack.response_classifier import (
    classify_slack_response,
)
from pyhookkit.adapters.outbound.slack.retry_policy import SlackRetryPolicy
from pyhookkit.adapters.outbound.slack.webhook_url import SlackWebhookUrl
from pyhookkit.domain.delivery import (
    DeliveryError,
    DeliveryErrorKind,
    DeliveryResult,
    DeliveryState,
)
from pyhookkit.json_types import JsonObject


class SlackWebhookDestination:
    """Deliver JSON to one Slack webhook with bounded retries."""

    def __init__(
        self,
        webhook_url: SlackWebhookUrl,
        *,
        transport: SlackHttpTransport | None = None,
        retry_policy: SlackRetryPolicy | None = None,
        timeouts: SlackHttpTimeouts | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._webhook_url = webhook_url
        self._transport = transport or HttpxSlackHttpTransport()
        self._retry_policy = retry_policy or SlackRetryPolicy()
        self._timeouts = timeouts or SlackHttpTimeouts()
        self._sleep = sleep
        self._jitter = jitter

    def send(self, payload: JsonObject) -> DeliveryResult:
        for attempt in range(1, self._retry_policy.max_attempts + 1):
            try:
                response = self._transport.post(
                    self._webhook_url.value,
                    payload,
                    self._timeouts,
                )
            except SlackTransportError:
                error = DeliveryError(
                    kind=DeliveryErrorKind.TRANSPORT,
                    retryable=True,
                )
                retry_after_seconds = None
            else:
                classification = classify_slack_response(response)
                if classification.succeeded:
                    return DeliveryResult(
                        state=DeliveryState.SUCCEEDED,
                        attempts=attempt,
                    )
                error = classification.error
                if error is None:
                    raise RuntimeError("failed classification must contain an error")
                retry_after_seconds = classification.retry_after_seconds

            if not error.retryable or attempt == self._retry_policy.max_attempts:
                return DeliveryResult(
                    state=DeliveryState.FAILED,
                    attempts=attempt,
                    error=error,
                )
            delay = self._retry_policy.delay(
                completed_attempts=attempt,
                retry_after_seconds=retry_after_seconds,
                jitter=self._jitter(),
            )
            self._sleep(delay)

        raise RuntimeError("Slack delivery loop exhausted without a result")
