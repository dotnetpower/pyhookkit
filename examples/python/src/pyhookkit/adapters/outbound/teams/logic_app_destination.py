"""Azure Logic App delivery for Microsoft Teams cards."""

import random
import time
from collections.abc import Callable

import httpx

from pyhookkit.adapters.outbound.teams.http_delivery import deliver_teams_http
from pyhookkit.adapters.outbound.teams.logic_app_url import TeamsLogicAppUrl
from pyhookkit.adapters.outbound.teams.retry_policy import TeamsRetryPolicy
from pyhookkit.domain.delivery import DeliveryResult
from pyhookkit.json_types import JsonObject


class TeamsLogicAppDestination:
    """Deliver one routed Adaptive Card request to an Azure Logic App."""

    def __init__(
        self,
        logic_app_url: TeamsLogicAppUrl,
        *,
        post: Callable[..., httpx.Response] = httpx.post,
        timeout_seconds: float = 30.0,
        retry_policy: TeamsRetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Teams Logic App timeout must be positive")
        self._logic_app_url = logic_app_url
        self._post = post
        self._timeout_seconds = timeout_seconds
        self._retry_policy = retry_policy
        self._sleep = sleep
        self._jitter = jitter

    def send(self, request: JsonObject) -> DeliveryResult:
        return deliver_teams_http(
            self._logic_app_url.value,
            request,
            post=self._post,
            timeout_seconds=self._timeout_seconds,
            retry_policy=self._retry_policy,
            sleep=self._sleep,
            jitter=self._jitter,
        )
