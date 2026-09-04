"""SQLite-backed central notification router tests."""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from pyhookkit.adapters.outbound.sqlite_route_store import (
    SqliteRouteStore,
    StoredDestination,
)
from pyhookkit.application.notification_router import (
    NotificationConflictError,
    NotificationRouter,
    RouteNotConfiguredError,
)
from pyhookkit.domain.delivery import (
    DeliveryError,
    DeliveryErrorKind,
    DeliveryResult,
    DeliveryState,
)
from pyhookkit.domain.notification import CanonicalNotification, Severity
from pyhookkit.domain.routing import NotificationState, TargetDeliveryState

_NOW = datetime(2026, 9, 4, 1, 0, tzinfo=UTC)
_CHANNEL_LINK = (
    "https://teams.cloud.microsoft/l/channel/"
    "19%3Aexample-channel%40thread.tacv2/General"
    "?groupId=11111111-1111-4111-8111-111111111111"
    "&tenantId=22222222-2222-4222-8222-222222222222"
)


def _notification(*, body: str = "Deployment completed") -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="router-event-001",
        route="release-notifications",
        title="Deployment result",
        body=body,
        severity=Severity.SUCCESS,
    )


def _store(path: Path) -> SqliteRouteStore:
    store = SqliteRouteStore(path)
    store.configure_destination(
        StoredDestination(
            target_id="teams-staging",
            route="release-notifications",
            provider="teams-workflow",
            endpoint_environment_variable="TEAMS_WORKFLOW_URL",
            channel_link=_CHANNEL_LINK,
            enabled=True,
        )
    )
    store.configure_destination(
        StoredDestination(
            target_id="slack-staging",
            route="release-notifications",
            provider="slack",
            endpoint_environment_variable="SLACK_WEBHOOK_URL",
            channel_link=None,
            enabled=True,
        )
    )
    return store


class StubDelivery:
    def __init__(self) -> None:
        self.targets: list[str] = []

    def deliver(
        self,
        target_id: str,
        notification: CanonicalNotification,
    ) -> DeliveryResult:
        assert notification.event_id == "router-event-001"
        self.targets.append(target_id)
        if target_id == "slack-staging":
            return DeliveryResult(DeliveryState.SUCCEEDED, attempts=1)
        return DeliveryResult(
            DeliveryState.FAILED,
            attempts=2,
            error=DeliveryError(
                DeliveryErrorKind.RATE_LIMITED,
                retryable=True,
                status_code=429,
            ),
        )


def test_router_fans_out_and_records_partial_failure(tmp_path: Path) -> None:
    database = tmp_path / "router.sqlite3"
    store = _store(database)
    delivery = StubDelivery()
    router = NotificationRouter(store, delivery, clock=lambda: _NOW)

    receipt = router.submit("gitlab", _notification())
    queued = router.status("gitlab", receipt.notification_id)

    assert receipt.duplicate is False
    assert queued is not None
    assert queued.state is NotificationState.QUEUED
    assert [item.target_id for item in queued.deliveries] == [
        "slack-staging",
        "teams-staging",
    ]

    assert router.drain(limit=10) == 2
    completed = router.status("gitlab", receipt.notification_id)

    assert completed is not None
    assert completed.state is NotificationState.PARTIAL_FAILED
    assert completed.deliveries[0].state is TargetDeliveryState.SUCCEEDED
    assert completed.deliveries[1].state is TargetDeliveryState.FAILED
    assert completed.deliveries[1].attempts == 2
    assert completed.deliveries[1].error_kind is DeliveryErrorKind.RATE_LIMITED
    assert completed.deliveries[1].status_code == 429
    assert router.deliver_next() is False
    assert database.stat().st_mode & 0o777 == 0o600


def test_duplicate_is_idempotent_and_changed_content_conflicts(
    tmp_path: Path,
) -> None:
    router = NotificationRouter(
        _store(tmp_path / "router.sqlite3"),
        StubDelivery(),
        clock=lambda: _NOW,
    )

    first = router.submit("argocd", _notification())
    duplicate = router.submit("argocd", _notification())

    assert duplicate.notification_id == first.notification_id
    assert duplicate.duplicate is True
    assert duplicate.state is NotificationState.QUEUED
    with pytest.raises(NotificationConflictError, match="different content"):
        router.submit("argocd", _notification(body="Changed content"))


def test_router_rejects_unknown_route_and_hides_other_producer_status(
    tmp_path: Path,
) -> None:
    router = NotificationRouter(
        _store(tmp_path / "router.sqlite3"),
        StubDelivery(),
        clock=lambda: _NOW,
    )
    unknown = CanonicalNotification(
        schema_version="1.0",
        event_id="unknown-route-001",
        route="unknown-route",
        body="Unknown",
        severity=Severity.INFO,
    )

    with pytest.raises(RouteNotConfiguredError, match="unknown-route"):
        router.submit("gitlab", unknown)

    receipt = router.submit("gitlab", _notification())
    assert router.status("argocd", receipt.notification_id) is None


def test_store_recovers_an_expired_delivery_lease(tmp_path: Path) -> None:
    store = _store(tmp_path / "router.sqlite3")
    router = NotificationRouter(store, StubDelivery(), clock=lambda: _NOW)
    router.submit("gitlab", _notification())

    first = store.claim_next(now=_NOW, lease_duration=timedelta(minutes=5))
    recovered = store.claim_next(
        now=_NOW + timedelta(minutes=6),
        lease_duration=timedelta(minutes=5),
    )

    assert first is not None
    assert recovered is not None
    assert recovered.target_id == first.target_id


def test_router_validates_application_boundaries(tmp_path: Path) -> None:
    store = _store(tmp_path / "router.sqlite3")

    with pytest.raises(ValueError, match="lease duration"):
        NotificationRouter(
            store,
            StubDelivery(),
            lease_duration=timedelta(0),
        )

    router = NotificationRouter(store, StubDelivery())
    with pytest.raises(ValueError, match="producer"):
        router.submit("GitLab", _notification())
    with pytest.raises(ValueError, match="notification ID"):
        router.status("gitlab", " ")
    with pytest.raises(ValueError, match="drain limit"):
        router.drain(limit=0)


def test_store_lists_and_updates_non_secret_destinations(tmp_path: Path) -> None:
    store = _store(tmp_path / "router.sqlite3")
    store.configure_destination(
        StoredDestination(
            "slack-staging",
            "release-notifications",
            "slack",
            "NEW_SLACK_WEBHOOK_URL",
            None,
            False,
        )
    )

    destinations = store.destinations()

    assert len(destinations) == 2
    assert destinations[0].endpoint_environment_variable == "NEW_SLACK_WEBHOOK_URL"
    assert destinations[0].enabled is False
    teams = destinations[1]
    assert teams.tenant_id == "22222222-2222-4222-8222-222222222222"
    assert teams.team_id == "11111111-1111-4111-8111-111111111111"
    assert teams.channel_id == "19:example-channel@thread.tacv2"
    assert teams.channel_name == "General"


def test_store_migrates_existing_channel_links_to_metadata(tmp_path: Path) -> None:
    database = tmp_path / "router.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE route_destinations (
                target_id TEXT PRIMARY KEY,
                route TEXT NOT NULL,
                provider TEXT NOT NULL,
                endpoint_environment_variable TEXT NOT NULL,
                channel_link TEXT,
                enabled INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO route_destinations
                (target_id, route, provider, endpoint_environment_variable,
                 channel_link, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "teams-staging",
                "release-notifications",
                "teams-workflow",
                "TEAMS_WORKFLOW_URL",
                _CHANNEL_LINK,
                1,
            ),
        )

    destination = SqliteRouteStore(database).destination("teams-staging")

    assert destination is not None
    assert destination.tenant_id == "22222222-2222-4222-8222-222222222222"
    assert destination.team_id == "11111111-1111-4111-8111-111111111111"
    assert destination.channel_id == "19:example-channel@thread.tacv2"
    assert destination.channel_name == "General"


def test_store_reports_delivering_and_all_failed_states(tmp_path: Path) -> None:
    store = SqliteRouteStore(tmp_path / "router.sqlite3")
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
    receipt = store.submit("gitlab", _notification())
    delivery = store.claim_next(now=_NOW, lease_duration=timedelta(minutes=5))

    assert delivery is not None
    delivering = store.status("gitlab", receipt.notification_id)
    assert delivering is not None
    assert delivering.state is NotificationState.DELIVERING

    failure = DeliveryResult(
        DeliveryState.FAILED,
        attempts=1,
        error=DeliveryError(
            DeliveryErrorKind.PERMANENT_PROVIDER,
            retryable=False,
        ),
    )
    store.complete(delivery, failure, completed_at=_NOW)
    failed = store.status("gitlab", receipt.notification_id)

    assert failed is not None
    assert failed.state is NotificationState.FAILED
    duplicate = store.submit("gitlab", _notification())
    assert duplicate.state is NotificationState.FAILED
    with pytest.raises(RuntimeError, match="no longer active"):
        store.complete(delivery, failure, completed_at=_NOW)


@pytest.mark.parametrize(
    "destination",
    [
        StoredDestination(
            "Invalid",
            "release-notifications",
            "slack",
            "SLACK_WEBHOOK_URL",
            None,
            True,
        ),
        StoredDestination(
            "slack-staging",
            "release-notifications",
            "smtp",
            "SMTP_URL",
            None,
            True,
        ),
        StoredDestination(
            "teams-staging",
            "release-notifications",
            "teams-workflow",
            "TEAMS_WORKFLOW_URL",
            None,
            True,
        ),
        StoredDestination(
            "slack-staging",
            "release-notifications",
            "slack",
            "invalid-env",
            None,
            True,
        ),
        StoredDestination(
            "slack-staging",
            "release-notifications",
            "slack",
            "SLACK_WEBHOOK_URL",
            _CHANNEL_LINK,
            True,
        ),
    ],
)
def test_store_rejects_invalid_destination_configuration(
    tmp_path: Path,
    destination: StoredDestination,
) -> None:
    store = SqliteRouteStore(tmp_path / "router.sqlite3")

    with pytest.raises(ValueError):
        store.configure_destination(destination)
