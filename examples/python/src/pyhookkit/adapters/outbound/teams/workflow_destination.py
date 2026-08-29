"""Microsoft Teams Workflow delivery."""

import random
import time
from collections.abc import Callable

import httpx

from pyhookkit.adapters.outbound.teams.http_delivery import deliver_teams_http
from pyhookkit.adapters.outbound.teams.retry_policy import TeamsRetryPolicy
from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.domain.delivery import DeliveryResult
from pyhookkit.json_types import JsonObject


class TeamsWorkflowDestination:
    """Deliver one Adaptive Card envelope to a Teams Workflow."""

    def __init__(
        self,
        workflow_url: TeamsWorkflowUrl,
        *,
        post: Callable[..., httpx.Response] = httpx.post,
        timeout_seconds: float = 15.0,
        retry_policy: TeamsRetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Teams Workflow timeout must be positive")
        self._workflow_url = workflow_url
        self._post = post
        self._timeout_seconds = timeout_seconds
        self._retry_policy = retry_policy
        self._sleep = sleep
        self._jitter = jitter

    def send(self, payload: JsonObject) -> DeliveryResult:
        return deliver_teams_http(
            self._workflow_url.value,
            payload,
            post=self._post,
            timeout_seconds=self._timeout_seconds,
            retry_policy=self._retry_policy,
            sleep=self._sleep,
            jitter=self._jitter,
        )
