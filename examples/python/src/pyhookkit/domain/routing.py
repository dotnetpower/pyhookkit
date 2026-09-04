"""Provider-neutral central notification routing outcomes."""

from dataclasses import dataclass
from enum import StrEnum

from pyhookkit.domain.delivery import DeliveryErrorKind
from pyhookkit.domain.notification import CanonicalNotification


class NotificationState(StrEnum):
    """Aggregate state of one routed notification."""

    QUEUED = "queued"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class TargetDeliveryState(StrEnum):
    """State of delivery to one configured route target."""

    QUEUED = "queued"
    DELIVERING = "delivering"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SubmissionReceipt:
    """Durable acceptance of one canonical notification."""

    notification_id: str
    duplicate: bool
    state: NotificationState


@dataclass(frozen=True, slots=True)
class TargetDeliveryStatus:
    """Redacted delivery status for one opaque route target."""

    target_id: str
    state: TargetDeliveryState
    attempts: int = 0
    error_kind: DeliveryErrorKind | None = None
    status_code: int | None = None

    def __post_init__(self) -> None:
        if not self.target_id.strip():
            raise ValueError("target ID must not be blank")
        if self.attempts < 0:
            raise ValueError("target delivery attempts must not be negative")
        if self.state is TargetDeliveryState.FAILED and self.error_kind is None:
            raise ValueError("failed target delivery must contain an error kind")
        if self.state is not TargetDeliveryState.FAILED and self.error_kind is not None:
            raise ValueError("non-failed target delivery cannot contain an error kind")


@dataclass(frozen=True, slots=True)
class RoutedNotificationStatus:
    """Aggregate and per-target status for one notification."""

    notification_id: str
    event_id: str
    state: NotificationState
    deliveries: tuple[TargetDeliveryStatus, ...]

    def __post_init__(self) -> None:
        if not self.notification_id.strip():
            raise ValueError("notification ID must not be blank")
        if not self.event_id.strip():
            raise ValueError("event ID must not be blank")
        if not self.deliveries:
            raise ValueError("routed notification must contain a delivery")


@dataclass(frozen=True, slots=True)
class PendingTargetDelivery:
    """One leased delivery task read from durable storage."""

    notification_id: str
    target_id: str
    notification: CanonicalNotification
