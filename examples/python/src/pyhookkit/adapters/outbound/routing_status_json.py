"""Central routing outcomes serialized without provider details."""

from pyhookkit.domain.routing import RoutedNotificationStatus, SubmissionReceipt
from pyhookkit.json_types import JsonObject, JsonValue


def submission_receipt_to_json(receipt: SubmissionReceipt) -> JsonObject:
    """Serialize a durable submission receipt."""
    return {
        "notificationId": receipt.notification_id,
        "duplicate": receipt.duplicate,
        "state": "queued",
    }


def routed_notification_status_to_json(
    status: RoutedNotificationStatus,
) -> JsonObject:
    """Serialize aggregate and target-level redacted status."""
    deliveries: list[JsonValue] = []
    for delivery in status.deliveries:
        item: JsonObject = {
            "targetId": delivery.target_id,
            "state": delivery.state.value,
            "attempts": delivery.attempts,
        }
        if delivery.error_kind is not None:
            item["errorKind"] = delivery.error_kind.value
        if delivery.status_code is not None:
            item["statusCode"] = delivery.status_code
        deliveries.append(item)
    return {
        "notificationId": status.notification_id,
        "eventId": status.event_id,
        "state": status.state.value,
        "deliveries": deliveries,
    }
