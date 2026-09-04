"""Application service for durable central notification routing."""

import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.domain.routing import RoutedNotificationStatus, SubmissionReceipt
from pyhookkit.ports.notification_routing import (
    NotificationRouteStore,
    RoutedNotificationDelivery,
)

_PRODUCER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class RouteNotConfiguredError(ValueError):
    """A canonical route has no enabled delivery targets."""


class NotificationConflictError(ValueError):
    """A producer reused an event ID with different canonical content."""


class NotificationRouter:
    """Accept, inspect, and deliver canonical notifications."""

    def __init__(
        self,
        store: NotificationRouteStore,
        delivery: RoutedNotificationDelivery,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        lease_duration: timedelta = timedelta(minutes=5),
    ) -> None:
        if lease_duration <= timedelta(0):
            raise ValueError("delivery lease duration must be positive")
        self._store = store
        self._delivery = delivery
        self._clock = clock
        self._lease_duration = lease_duration

    def submit(
        self,
        producer: str,
        notification: CanonicalNotification,
    ) -> SubmissionReceipt:
        """Durably enqueue a notification for every configured route target."""
        _validate_producer(producer)
        return self._store.submit(producer, notification)

    def status(
        self,
        producer: str,
        notification_id: str,
    ) -> RoutedNotificationStatus | None:
        """Return status only when it belongs to the authenticated producer."""
        _validate_producer(producer)
        if not notification_id.strip():
            raise ValueError("notification ID must not be blank")
        return self._store.status(producer, notification_id)

    def deliver_next(self) -> bool:
        """Deliver one queued target, returning whether work was available."""
        delivery = self._store.claim_next(
            now=self._clock(),
            lease_duration=self._lease_duration,
        )
        if delivery is None:
            return False
        result = self._delivery.deliver(delivery.target_id, delivery.notification)
        self._store.complete(delivery, result, completed_at=self._clock())
        return True

    def drain(self, *, limit: int) -> int:
        """Deliver up to a bounded number of queued targets."""
        if limit < 1:
            raise ValueError("drain limit must be positive")
        delivered = 0
        while delivered < limit and self.deliver_next():
            delivered += 1
        return delivered


def _validate_producer(producer: str) -> None:
    if _PRODUCER.fullmatch(producer) is None:
        raise ValueError("producer must use lower-case kebab-case")
