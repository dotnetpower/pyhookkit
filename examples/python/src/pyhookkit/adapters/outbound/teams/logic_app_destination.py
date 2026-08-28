"""Azure Logic App delivery for Microsoft Teams cards."""

from collections.abc import Callable

import httpx

from pyhookkit.adapters.outbound.teams.http_delivery import deliver_teams_http
from pyhookkit.adapters.outbound.teams.logic_app_url import TeamsLogicAppUrl
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
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Teams Logic App timeout must be positive")
        self._logic_app_url = logic_app_url
        self._post = post
        self._timeout_seconds = timeout_seconds

    def send(self, request: JsonObject) -> DeliveryResult:
        return deliver_teams_http(
            self._logic_app_url.value,
            request,
            post=self._post,
            timeout_seconds=self._timeout_seconds,
        )
