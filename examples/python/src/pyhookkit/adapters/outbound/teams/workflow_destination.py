"""Microsoft Teams Workflow delivery."""

from collections.abc import Callable

import httpx

from pyhookkit.adapters.outbound.teams.http_delivery import deliver_teams_http
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
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Teams Workflow timeout must be positive")
        self._workflow_url = workflow_url
        self._post = post
        self._timeout_seconds = timeout_seconds

    def send(self, payload: JsonObject) -> DeliveryResult:
        return deliver_teams_http(
            self._workflow_url.value,
            payload,
            post=self._post,
            timeout_seconds=self._timeout_seconds,
        )
