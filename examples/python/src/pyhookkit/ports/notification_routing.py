"""Central notification routing boundaries."""

from datetime import datetime, timedelta
from typing import Protocol

from pyhookkit.domain.delivery import DeliveryResult
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.domain.routing import (
    PendingTargetDelivery,
    RoutedNotificationStatus,
    SubmissionReceipt,
)


class NotificationRouteStore(Protocol):
    """Persist routed notifications and target delivery state."""

    def submit(
        self,
        producer: str,
        notification: CanonicalNotification,
    ) -> SubmissionReceipt:
        """Atomically enqueue all configured targets for a notification."""
        ...

    def status(
        self,
        producer: str,
        notification_id: str,
    ) -> RoutedNotificationStatus | None:
        """Read a producer-owned notification status."""
        ...

    def claim_next(
        self,
        *,
        now: datetime,
        lease_duration: timedelta,
    ) -> PendingTargetDelivery | None:
        """Lease the oldest available target delivery."""
        ...

    def complete(
        self,
        delivery: PendingTargetDelivery,
        result: DeliveryResult,
        *,
        completed_at: datetime,
    ) -> None:
        """Persist a terminal provider delivery result."""
        ...


class RoutedNotificationDelivery(Protocol):
    """Deliver a notification through an opaque configured target."""

    def deliver(
        self,
        target_id: str,
        notification: CanonicalNotification,
    ) -> DeliveryResult:
        """Render and send one configured target delivery."""
        ...
