"""Provider delivery selected by non-secret SQLite destination configuration."""

from collections.abc import Callable, Mapping
from typing import Protocol

from pyhookkit.adapters.outbound.slack.message_renderer import SlackMessageRenderer
from pyhookkit.adapters.outbound.slack.webhook_destination import (
    SlackWebhookDestination,
)
from pyhookkit.adapters.outbound.slack.webhook_url import SlackWebhookUrl
from pyhookkit.adapters.outbound.sqlite_route_store import SqliteRouteStore
from pyhookkit.adapters.outbound.teams.channel_link import TeamsChannelLink
from pyhookkit.adapters.outbound.teams.message_renderer import TeamsMessageRenderer
from pyhookkit.adapters.outbound.teams.workflow_destination import (
    TeamsWorkflowDestination,
)
from pyhookkit.adapters.outbound.teams.workflow_request import (
    build_teams_workflow_request,
)
from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.domain.delivery import (
    DeliveryError,
    DeliveryErrorKind,
    DeliveryResult,
    DeliveryState,
)
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.json_types import JsonObject


class JsonDestination(Protocol):
    """Send one provider payload."""

    def send(self, payload: JsonObject) -> DeliveryResult:
        """Return a redacted provider result."""
        ...


class ConfiguredNotificationDelivery:
    """Resolve one target and deliver through its provider adapter."""

    def __init__(
        self,
        store: SqliteRouteStore,
        environment: Mapping[str, str],
        *,
        slack_destination: Callable[[SlackWebhookUrl], JsonDestination] = (
            SlackWebhookDestination
        ),
        teams_destination: Callable[[TeamsWorkflowUrl], JsonDestination] = (
            TeamsWorkflowDestination
        ),
    ) -> None:
        self._store = store
        self._environment = environment
        self._slack_destination = slack_destination
        self._teams_destination = teams_destination

    def deliver(
        self,
        target_id: str,
        notification: CanonicalNotification,
    ) -> DeliveryResult:
        """Render and send without exposing endpoint credentials."""
        destination = self._store.destination(target_id)
        if destination is None:
            return _failure(DeliveryErrorKind.PERMANENT_PROVIDER)
        raw_endpoint = self._environment.get(
            destination.endpoint_environment_variable,
            "",
        ).strip()
        if not raw_endpoint:
            return _failure(DeliveryErrorKind.AUTHENTICATION)

        try:
            if destination.provider == "slack":
                payload = SlackMessageRenderer().render(notification)
                return self._slack_destination(SlackWebhookUrl(raw_endpoint)).send(
                    payload
                )
            if destination.provider == "teams-workflow":
                if destination.channel_link is None:
                    return _failure(DeliveryErrorKind.PERMANENT_PROVIDER)
                envelope = TeamsMessageRenderer(hero_image_url=None).render(
                    notification
                )
                request = build_teams_workflow_request(
                    envelope,
                    TeamsChannelLink(destination.channel_link),
                )
                return self._teams_destination(TeamsWorkflowUrl(raw_endpoint)).send(
                    request
                )
        except ValueError:
            return _failure(DeliveryErrorKind.INVALID_PAYLOAD)
        return _failure(DeliveryErrorKind.PERMANENT_PROVIDER)


def _failure(kind: DeliveryErrorKind) -> DeliveryResult:
    return DeliveryResult(
        DeliveryState.FAILED,
        attempts=1,
        error=DeliveryError(kind, retryable=False),
    )
