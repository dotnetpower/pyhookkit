"""Delivery result JSON contract serialization."""

from pyhookkit.domain.delivery import DeliveryResult
from pyhookkit.json_types import JsonObject


def delivery_result_to_json(result: DeliveryResult) -> JsonObject:
    """Serialize a delivery result using the language-neutral field names."""
    payload: JsonObject = {
        "state": result.state.value,
        "attempts": result.attempts,
    }
    if result.error is not None:
        error: JsonObject = {
            "kind": result.error.kind.value,
            "retryable": result.error.retryable,
        }
        if result.error.status_code is not None:
            error["statusCode"] = result.error.status_code
        payload["error"] = error
    return payload
