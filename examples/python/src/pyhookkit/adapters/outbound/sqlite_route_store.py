"""SQLite route configuration, outbox, and delivery status storage."""

import json
import re
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import uuid4

from pyhookkit.adapters.inbound.canonical_notification_json import (
    canonical_notification_from_json,
)
from pyhookkit.adapters.outbound.canonical_notification_json import (
    canonical_notification_to_json,
)
from pyhookkit.adapters.outbound.teams.channel_link import TeamsChannelLink
from pyhookkit.adapters.outbound.teams.channel_metadata import (
    TeamsChannelMembershipType,
)
from pyhookkit.application.notification_router import (
    NotificationConflictError,
    RouteNotConfiguredError,
)
from pyhookkit.domain.delivery import DeliveryErrorKind, DeliveryResult, DeliveryState
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.domain.routing import (
    NotificationState,
    PendingTargetDelivery,
    RoutedNotificationStatus,
    SubmissionReceipt,
    TargetDeliveryState,
    TargetDeliveryStatus,
)

_TARGET_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ROUTE = _TARGET_ID
_ENVIRONMENT_VARIABLE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_PROVIDERS = frozenset({"slack", "teams-workflow"})


@dataclass(frozen=True, slots=True)
class StoredDestination:
    """Provider configuration whose credential is referenced by environment."""

    target_id: str
    route: str
    provider: str
    endpoint_environment_variable: str
    channel_link: str | None
    enabled: bool
    tenant_id: str | None = None
    team_id: str | None = None
    channel_id: str | None = None
    channel_name: str | None = None
    membership_type: str | None = None


@dataclass(frozen=True, slots=True)
class StoredNotificationSummary:
    """Redacted recent notification activity for administration views."""

    notification_id: str
    producer: str
    event_id: str
    created_at: str
    state: NotificationState
    deliveries: tuple[TargetDeliveryStatus, ...]


class SqliteRouteStore:
    """Persist route configuration and an at-least-once delivery outbox."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self._path.chmod(0o600)

    def configure_destination(self, destination: StoredDestination) -> None:
        """Create or replace one non-secret route destination."""
        channel_link = _validate_destination(destination)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO route_destinations (
                    target_id,
                    route,
                    provider,
                    endpoint_environment_variable,
                    channel_link,
                    tenant_id,
                    team_id,
                    channel_id,
                    channel_name,
                    membership_type,
                    enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(target_id) DO UPDATE SET
                    route = excluded.route,
                    provider = excluded.provider,
                    endpoint_environment_variable =
                        excluded.endpoint_environment_variable,
                    channel_link = excluded.channel_link,
                    tenant_id = excluded.tenant_id,
                    team_id = excluded.team_id,
                    channel_id = excluded.channel_id,
                    channel_name = excluded.channel_name,
                    membership_type = excluded.membership_type,
                    enabled = excluded.enabled
                """,
                (
                    destination.target_id,
                    destination.route,
                    destination.provider,
                    destination.endpoint_environment_variable,
                    destination.channel_link,
                    str(channel_link.tenant_id) if channel_link is not None else None,
                    str(channel_link.team_id) if channel_link is not None else None,
                    channel_link.channel_id if channel_link is not None else None,
                    channel_link.channel_name if channel_link is not None else None,
                    destination.membership_type,
                    int(destination.enabled),
                ),
            )

    def destinations(self) -> tuple[StoredDestination, ...]:
        """List configured destinations without resolving credentials."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    target_id,
                    route,
                    provider,
                    endpoint_environment_variable,
                    channel_link,
                    tenant_id,
                    team_id,
                    channel_id,
                    channel_name,
                    membership_type,
                    enabled
                FROM route_destinations
                ORDER BY route, target_id
                """
            ).fetchall()
        return tuple(_destination_from_row(row) for row in rows)

    def destination(self, target_id: str) -> StoredDestination | None:
        """Read one destination by its opaque identifier."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT
                    target_id,
                    route,
                    provider,
                    endpoint_environment_variable,
                    channel_link,
                    tenant_id,
                    team_id,
                    channel_id,
                    channel_name,
                    membership_type,
                    enabled
                FROM route_destinations
                WHERE target_id = ?
                """,
                (target_id,),
            ).fetchone()
        return _destination_from_row(row) if row is not None else None

    def recent_notifications(
        self,
        *,
        limit: int = 50,
    ) -> tuple[StoredNotificationSummary, ...]:
        """List recent redacted notification activity without payload content."""
        if limit < 1 or limit > 100:
            raise ValueError("recent notification limit must be between 1 and 100")
        with self._connection() as connection:
            notification_rows = connection.execute(
                """
                SELECT notification_id, producer, event_id, created_at
                FROM routed_notifications
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            summaries: list[StoredNotificationSummary] = []
            for notification_row in notification_rows:
                notification_id = cast(str, notification_row["notification_id"])
                delivery_rows = connection.execute(
                    """
                    SELECT target_id, state, attempts, error_kind, status_code
                    FROM target_deliveries
                    WHERE notification_id = ?
                    ORDER BY target_id
                    """,
                    (notification_id,),
                ).fetchall()
                deliveries = tuple(
                    _delivery_status_from_row(row) for row in delivery_rows
                )
                summaries.append(
                    StoredNotificationSummary(
                        notification_id=notification_id,
                        producer=cast(str, notification_row["producer"]),
                        event_id=cast(str, notification_row["event_id"]),
                        created_at=cast(str, notification_row["created_at"]),
                        state=_aggregate_state(deliveries),
                        deliveries=deliveries,
                    )
                )
        return tuple(summaries)

    def record_direct_delivery(
        self,
        producer: str,
        notification: CanonicalNotification,
        target_id: str,
        result: DeliveryResult,
        *,
        completed_at: datetime,
    ) -> str:
        """Record one direct administration delivery without route fan-out."""
        notification_id = str(uuid4())
        timestamp = _timestamp(completed_at)
        payload = json.dumps(
            canonical_notification_to_json(notification),
            separators=(",", ":"),
            sort_keys=True,
        )
        state = (
            TargetDeliveryState.SUCCEEDED
            if result.state is DeliveryState.SUCCEEDED
            else TargetDeliveryState.FAILED
        )
        error_kind = result.error.kind.value if result.error is not None else None
        status_code = result.error.status_code if result.error is not None else None
        with self._transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM route_destinations WHERE target_id = ?",
                (target_id,),
            ).fetchone()
            if exists is None:
                raise ValueError("direct delivery target was not found")
            connection.execute(
                """
                INSERT INTO routed_notifications (
                    notification_id, producer, event_id, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    notification_id,
                    producer,
                    notification.event_id,
                    payload,
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO target_deliveries (
                    notification_id,
                    target_id,
                    state,
                    attempts,
                    error_kind,
                    status_code,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification_id,
                    target_id,
                    state.value,
                    result.attempts,
                    error_kind,
                    status_code,
                    timestamp,
                ),
            )
        return notification_id

    def submit(
        self,
        producer: str,
        notification: CanonicalNotification,
    ) -> SubmissionReceipt:
        """Atomically enqueue every enabled destination for a canonical route."""
        payload = json.dumps(
            canonical_notification_to_json(notification),
            separators=(",", ":"),
            sort_keys=True,
        )
        with self._transaction() as connection:
            existing = connection.execute(
                """
                SELECT notification_id, payload_json
                FROM routed_notifications
                WHERE producer = ? AND event_id = ?
                """,
                (producer, notification.event_id),
            ).fetchone()
            if existing is not None:
                if cast(str, existing["payload_json"]) != payload:
                    raise NotificationConflictError(
                        "event ID was already used with different content"
                    )
                return SubmissionReceipt(
                    notification_id=cast(str, existing["notification_id"]),
                    duplicate=True,
                    state=self._notification_state(
                        connection,
                        cast(str, existing["notification_id"]),
                    ),
                )

            target_rows = connection.execute(
                """
                SELECT target_id
                FROM route_destinations
                WHERE route = ? AND enabled = 1
                ORDER BY target_id
                """,
                (notification.route,),
            ).fetchall()
            if not target_rows:
                raise RouteNotConfiguredError(
                    f"notification route is not configured: {notification.route}"
                )

            notification_id = str(uuid4())
            timestamp = _timestamp(datetime.now(UTC))
            connection.execute(
                """
                INSERT INTO routed_notifications (
                    notification_id,
                    producer,
                    event_id,
                    payload_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    notification_id,
                    producer,
                    notification.event_id,
                    payload,
                    timestamp,
                ),
            )
            connection.executemany(
                """
                INSERT INTO target_deliveries (
                    notification_id,
                    target_id,
                    state,
                    attempts,
                    updated_at
                ) VALUES (?, ?, 'queued', 0, ?)
                """,
                (
                    (
                        notification_id,
                        cast(str, row["target_id"]),
                        timestamp,
                    )
                    for row in target_rows
                ),
            )
        return SubmissionReceipt(
            notification_id=notification_id,
            duplicate=False,
            state=NotificationState.QUEUED,
        )

    def submit_to_target(
        self,
        producer: str,
        target_id: str,
        notification: CanonicalNotification,
    ) -> SubmissionReceipt:
        """Atomically enqueue one configured target without route fan-out."""
        payload = json.dumps(
            canonical_notification_to_json(notification),
            separators=(",", ":"),
            sort_keys=True,
        )
        with self._transaction() as connection:
            existing = connection.execute(
                """
                SELECT notification.notification_id, notification.payload_json
                FROM routed_notifications AS notification
                JOIN target_deliveries AS delivery
                    ON delivery.notification_id = notification.notification_id
                WHERE notification.producer = ?
                  AND notification.event_id = ?
                  AND delivery.target_id = ?
                """,
                (producer, notification.event_id, target_id),
            ).fetchone()
            if existing is not None:
                if cast(str, existing["payload_json"]) != payload:
                    raise NotificationConflictError(
                        "event ID was already used with different content"
                    )
                notification_id = cast(str, existing["notification_id"])
                return SubmissionReceipt(
                    notification_id=notification_id,
                    duplicate=True,
                    state=self._notification_state(connection, notification_id),
                )
            reused_event = connection.execute(
                """
                SELECT 1 FROM routed_notifications
                WHERE producer = ? AND event_id = ?
                """,
                (producer, notification.event_id),
            ).fetchone()
            if reused_event is not None:
                raise NotificationConflictError(
                    "event ID was already used for a different target"
                )
            destination = connection.execute(
                """
                SELECT route FROM route_destinations
                WHERE target_id = ? AND enabled = 1
                """,
                (target_id,),
            ).fetchone()
            if destination is None or destination["route"] != notification.route:
                raise RouteNotConfiguredError(
                    f"notification target is not configured for route: {target_id}"
                )
            notification_id = str(uuid4())
            timestamp = _timestamp(datetime.now(UTC))
            connection.execute(
                """
                INSERT INTO routed_notifications (
                    notification_id, producer, event_id, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    notification_id,
                    producer,
                    notification.event_id,
                    payload,
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO target_deliveries (
                    notification_id, target_id, state, attempts, updated_at
                ) VALUES (?, ?, 'queued', 0, ?)
                """,
                (notification_id, target_id, timestamp),
            )
        return SubmissionReceipt(
            notification_id=notification_id,
            duplicate=False,
            state=NotificationState.QUEUED,
        )

    def status(
        self,
        producer: str,
        notification_id: str,
    ) -> RoutedNotificationStatus | None:
        """Read producer-owned aggregate and per-target delivery state."""
        with self._connection() as connection:
            notification_row = connection.execute(
                """
                SELECT event_id
                FROM routed_notifications
                WHERE notification_id = ? AND producer = ?
                """,
                (notification_id, producer),
            ).fetchone()
            if notification_row is None:
                return None
            delivery_rows = connection.execute(
                """
                SELECT target_id, state, attempts, error_kind, status_code
                FROM target_deliveries
                WHERE notification_id = ?
                ORDER BY target_id
                """,
                (notification_id,),
            ).fetchall()

        deliveries = tuple(_delivery_status_from_row(row) for row in delivery_rows)
        return RoutedNotificationStatus(
            notification_id=notification_id,
            event_id=cast(str, notification_row["event_id"]),
            state=_aggregate_state(deliveries),
            deliveries=deliveries,
        )

    def claim_next(
        self,
        *,
        now: datetime,
        lease_duration: timedelta,
    ) -> PendingTargetDelivery | None:
        """Lease one queued delivery and recover expired leases."""
        now_value = _timestamp(now)
        lease_cutoff = _timestamp(now - lease_duration)
        with self._transaction() as connection:
            connection.execute(
                """
                UPDATE target_deliveries
                SET state = 'queued', locked_at = NULL, updated_at = ?
                WHERE state = 'delivering' AND locked_at < ?
                """,
                (now_value, lease_cutoff),
            )
            row = connection.execute(
                """
                SELECT
                    delivery.notification_id,
                    delivery.target_id,
                    notification.payload_json
                FROM target_deliveries AS delivery
                JOIN routed_notifications AS notification
                    ON notification.notification_id = delivery.notification_id
                WHERE delivery.state = 'queued'
                ORDER BY notification.created_at, delivery.target_id
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            updated = connection.execute(
                """
                UPDATE target_deliveries
                SET state = 'delivering', locked_at = ?, updated_at = ?
                WHERE notification_id = ? AND target_id = ? AND state = 'queued'
                """,
                (
                    now_value,
                    now_value,
                    cast(str, row["notification_id"]),
                    cast(str, row["target_id"]),
                ),
            )
            if updated.rowcount != 1:
                raise RuntimeError("failed to lease queued target delivery")

        payload: object = json.loads(cast(str, row["payload_json"]))
        return PendingTargetDelivery(
            notification_id=cast(str, row["notification_id"]),
            target_id=cast(str, row["target_id"]),
            notification=canonical_notification_from_json(
                payload,
                source_name="stored notification",
            ),
        )

    def complete(
        self,
        delivery: PendingTargetDelivery,
        result: DeliveryResult,
        *,
        completed_at: datetime,
    ) -> None:
        """Store one terminal redacted provider result."""
        error_kind = result.error.kind.value if result.error is not None else None
        status_code = result.error.status_code if result.error is not None else None
        state = (
            TargetDeliveryState.SUCCEEDED
            if result.state is DeliveryState.SUCCEEDED
            else TargetDeliveryState.FAILED
        )
        with self._connection() as connection:
            updated = connection.execute(
                """
                UPDATE target_deliveries
                SET
                    state = ?,
                    attempts = attempts + ?,
                    error_kind = ?,
                    status_code = ?,
                    locked_at = NULL,
                    updated_at = ?
                WHERE
                    notification_id = ?
                    AND target_id = ?
                    AND state = 'delivering'
                """,
                (
                    state.value,
                    result.attempts,
                    error_kind,
                    status_code,
                    _timestamp(completed_at),
                    delivery.notification_id,
                    delivery.target_id,
                ),
            )
            if updated.rowcount != 1:
                raise RuntimeError("target delivery lease is no longer active")

    def _notification_state(
        self,
        connection: sqlite3.Connection,
        notification_id: str,
    ) -> NotificationState:
        rows = connection.execute(
            """
            SELECT target_id, state, attempts, error_kind, status_code
            FROM target_deliveries
            WHERE notification_id = ?
            ORDER BY target_id
            """,
            (notification_id,),
        ).fetchall()
        return _aggregate_state(tuple(_delivery_status_from_row(row) for row in rows))

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS route_destinations (
                    target_id TEXT PRIMARY KEY,
                    route TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    endpoint_environment_variable TEXT NOT NULL,
                    channel_link TEXT,
                    tenant_id TEXT,
                    team_id TEXT,
                    channel_id TEXT,
                    channel_name TEXT,
                    membership_type TEXT,
                    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1))
                );

                CREATE INDEX IF NOT EXISTS route_destinations_route_idx
                    ON route_destinations(route, enabled);

                CREATE TABLE IF NOT EXISTS routed_notifications (
                    notification_id TEXT PRIMARY KEY,
                    producer TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(producer, event_id)
                );

                CREATE TABLE IF NOT EXISTS target_deliveries (
                    notification_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (
                        state IN ('queued', 'delivering', 'succeeded', 'failed')
                    ),
                    attempts INTEGER NOT NULL CHECK (attempts >= 0),
                    error_kind TEXT,
                    status_code INTEGER,
                    locked_at TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(notification_id, target_id),
                    FOREIGN KEY(notification_id)
                        REFERENCES routed_notifications(notification_id),
                    FOREIGN KEY(target_id)
                        REFERENCES route_destinations(target_id)
                );

                CREATE INDEX IF NOT EXISTS target_deliveries_state_idx
                    ON target_deliveries(state, updated_at);
                """
            )
            self._migrate_destination_metadata(connection)

    def _migrate_destination_metadata(self, connection: sqlite3.Connection) -> None:
        existing_columns = {
            cast(str, row["name"])
            for row in connection.execute(
                "PRAGMA table_info(route_destinations)"
            ).fetchall()
        }
        for column_name in (
            "tenant_id",
            "team_id",
            "channel_id",
            "channel_name",
            "membership_type",
        ):
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE route_destinations ADD COLUMN {column_name} TEXT"
                )
        rows = connection.execute(
            """
            SELECT target_id, channel_link
            FROM route_destinations
            WHERE provider = 'teams-workflow'
            """
        ).fetchall()
        for row in rows:
            raw_link = cast(str | None, row["channel_link"])
            if raw_link is None:
                raise ValueError(
                    "stored Teams Workflow destination has no channel link"
                )
            link = TeamsChannelLink(raw_link)
            connection.execute(
                """
                UPDATE route_destinations
                SET tenant_id = ?, team_id = ?, channel_id = ?, channel_name = ?
                WHERE target_id = ?
                """,
                (
                    str(link.tenant_id),
                    str(link.team_id),
                    link.channel_id,
                    link.channel_name,
                    cast(str, row["target_id"]),
                ),
            )

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Connection]:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            yield connection


def _validate_destination(
    destination: StoredDestination,
) -> TeamsChannelLink | None:
    if _TARGET_ID.fullmatch(destination.target_id) is None:
        raise ValueError("target ID must use lower-case kebab-case")
    if _ROUTE.fullmatch(destination.route) is None:
        raise ValueError("destination route must use lower-case kebab-case")
    if destination.provider not in _PROVIDERS:
        supported = ", ".join(sorted(_PROVIDERS))
        raise ValueError(f"destination provider must be one of: {supported}")
    if (
        _ENVIRONMENT_VARIABLE.fullmatch(destination.endpoint_environment_variable)
        is None
    ):
        raise ValueError("endpoint environment variable name is invalid")
    if destination.provider == "teams-workflow" and destination.channel_link is None:
        raise ValueError("Teams Workflow destination requires a channel link")
    if destination.provider == "slack" and destination.channel_link is not None:
        raise ValueError("Slack destination cannot contain a Teams channel link")
    if destination.membership_type is not None:
        try:
            membership_type = TeamsChannelMembershipType(destination.membership_type)
        except ValueError as error:
            raise ValueError("Teams channel membership type is invalid") from error
        if destination.provider != "teams-workflow":
            raise ValueError("Slack destination cannot contain Teams channel metadata")
        if membership_type is TeamsChannelMembershipType.SHARED:
            raise ValueError("shared Teams channels are not supported")
    if destination.channel_link is not None:
        return TeamsChannelLink(destination.channel_link)
    return None


def _destination_from_row(row: sqlite3.Row) -> StoredDestination:
    return StoredDestination(
        target_id=cast(str, row["target_id"]),
        route=cast(str, row["route"]),
        provider=cast(str, row["provider"]),
        endpoint_environment_variable=cast(
            str,
            row["endpoint_environment_variable"],
        ),
        channel_link=cast(str | None, row["channel_link"]),
        enabled=bool(row["enabled"]),
        tenant_id=cast(str | None, row["tenant_id"]),
        team_id=cast(str | None, row["team_id"]),
        channel_id=cast(str | None, row["channel_id"]),
        channel_name=cast(str | None, row["channel_name"]),
        membership_type=cast(str | None, row["membership_type"]),
    )


def _delivery_status_from_row(row: sqlite3.Row) -> TargetDeliveryStatus:
    raw_error_kind = cast(str | None, row["error_kind"])
    return TargetDeliveryStatus(
        target_id=cast(str, row["target_id"]),
        state=TargetDeliveryState(cast(str, row["state"])),
        attempts=cast(int, row["attempts"]),
        error_kind=(
            DeliveryErrorKind(raw_error_kind) if raw_error_kind is not None else None
        ),
        status_code=cast(int | None, row["status_code"]),
    )


def _aggregate_state(
    deliveries: tuple[TargetDeliveryStatus, ...],
) -> NotificationState:
    states = {delivery.state for delivery in deliveries}
    if states == {TargetDeliveryState.SUCCEEDED}:
        return NotificationState.DELIVERED
    if states == {TargetDeliveryState.FAILED}:
        return NotificationState.FAILED
    if states <= {TargetDeliveryState.SUCCEEDED, TargetDeliveryState.FAILED}:
        return NotificationState.PARTIAL_FAILED
    if states == {TargetDeliveryState.QUEUED}:
        return NotificationState.QUEUED
    return NotificationState.DELIVERING


def _timestamp(value: datetime) -> str:
    if value.utcoffset() is None:
        raise ValueError("routing timestamps must include a UTC offset")
    return value.astimezone(UTC).isoformat()
