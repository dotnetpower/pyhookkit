"""Provider delivery selected from SQLite route configuration."""

from pathlib import Path
from typing import ClassVar

from pyhookkit.adapters.outbound.configured_notification_delivery import (
    ConfiguredNotificationDelivery,
)
from pyhookkit.adapters.outbound.slack.webhook_url import SlackWebhookUrl
from pyhookkit.adapters.outbound.sqlite_route_store import (
    SqliteRouteStore,
    StoredDestination,
)
from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.domain.delivery import DeliveryErrorKind, DeliveryResult, DeliveryState
from pyhookkit.domain.notification import CanonicalNotification, Severity
from pyhookkit.json_types import JsonObject

_TEAMS_URL = (
    "https://default-example.environment.api.powerplatform.com/"
    "workflows/example/triggers/manual/paths/invoke?sig=synthetic"
)
_CHANNEL_LINK = (
    "https://teams.microsoft.com/l/channel/"
    "19%3Aexample-channel%40thread.tacv2/General"
    "?groupId=11111111-1111-4111-8111-111111111111"
    "&tenantId=22222222-2222-4222-8222-222222222222"
)


def _notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="configured-delivery-001",
        route="release-notifications",
        body="Deployment completed",
        severity=Severity.SUCCESS,
    )


class CapturingDestination:
    payloads: ClassVar[list[JsonObject]] = []

    def send(self, payload: JsonObject) -> DeliveryResult:
        self.payloads.append(payload)
        return DeliveryResult(DeliveryState.SUCCEEDED, attempts=1)


def test_configured_delivery_sends_slack_and_teams_payloads(tmp_path: Path) -> None:
    store = SqliteRouteStore(tmp_path / "router.sqlite3")
    store.configure_destination(
        StoredDestination(
            "slack-staging",
            "release-notifications",
            "slack",
            "SLACK_WEBHOOK_URL",
            None,
            True,
        )
    )
    store.configure_destination(
        StoredDestination(
            "teams-staging",
            "release-notifications",
            "teams-workflow",
            "TEAMS_WORKFLOW_URL",
            _CHANNEL_LINK,
            True,
        )
    )
    CapturingDestination.payloads = []
    delivery = ConfiguredNotificationDelivery(
        store,
        {
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/S",
            "TEAMS_WORKFLOW_URL": _TEAMS_URL,
        },
        slack_destination=lambda url: _capture_slack(url),
        teams_destination=lambda url: _capture_teams(url),
    )

    slack_result = delivery.deliver("slack-staging", _notification())
    teams_result = delivery.deliver("teams-staging", _notification())

    assert slack_result.state is DeliveryState.SUCCEEDED
    assert teams_result.state is DeliveryState.SUCCEEDED

    assert CapturingDestination.payloads[0]["attachments"]
    assert CapturingDestination.payloads[1]["channelLink"] == _CHANNEL_LINK
    assert CapturingDestination.payloads[1]["teamId"] == (
        "11111111-1111-4111-8111-111111111111"
    )


def test_configured_delivery_redacts_configuration_failures(tmp_path: Path) -> None:
    store = SqliteRouteStore(tmp_path / "router.sqlite3")
    store.configure_destination(
        StoredDestination(
            "slack-staging",
            "release-notifications",
            "slack",
            "SLACK_WEBHOOK_URL",
            None,
            True,
        )
    )
    delivery = ConfiguredNotificationDelivery(store, {})

    missing_target = delivery.deliver("missing", _notification())
    missing_secret = delivery.deliver("slack-staging", _notification())

    assert missing_target.error is not None
    assert missing_target.error.kind is DeliveryErrorKind.PERMANENT_PROVIDER
    assert missing_secret.error is not None
    assert missing_secret.error.kind is DeliveryErrorKind.AUTHENTICATION


def test_configured_delivery_classifies_invalid_endpoint(tmp_path: Path) -> None:
    store = SqliteRouteStore(tmp_path / "router.sqlite3")
    store.configure_destination(
        StoredDestination(
            "slack-staging",
            "release-notifications",
            "slack",
            "SLACK_WEBHOOK_URL",
            None,
            True,
        )
    )

    result = ConfiguredNotificationDelivery(
        store,
        {"SLACK_WEBHOOK_URL": "https://example.com/not-slack"},
    ).deliver("slack-staging", _notification())

    assert result.error is not None
    assert result.error.kind is DeliveryErrorKind.INVALID_PAYLOAD


def _capture_slack(url: SlackWebhookUrl) -> CapturingDestination:
    assert url.value.startswith("https://hooks.slack.com/")
    return CapturingDestination()


def _capture_teams(url: TeamsWorkflowUrl) -> CapturingDestination:
    assert url.value == _TEAMS_URL
    return CapturingDestination()
