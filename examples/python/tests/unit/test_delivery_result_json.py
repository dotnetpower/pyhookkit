"""Delivery result JSON contract serialization tests."""

from pyhookkit.adapters.outbound.delivery_result_json import (
    delivery_result_to_json,
)
from pyhookkit.domain.delivery import (
    DeliveryError,
    DeliveryErrorKind,
    DeliveryResult,
    DeliveryState,
)


def test_success_result_omits_error() -> None:
    result = DeliveryResult(DeliveryState.SUCCEEDED, attempts=1)

    assert delivery_result_to_json(result) == {
        "state": "succeeded",
        "attempts": 1,
    }


def test_failure_result_uses_contract_field_names() -> None:
    result = DeliveryResult(
        DeliveryState.FAILED,
        attempts=3,
        error=DeliveryError(
            DeliveryErrorKind.RATE_LIMITED,
            retryable=True,
            status_code=429,
        ),
    )

    assert delivery_result_to_json(result) == {
        "state": "failed",
        "attempts": 3,
        "error": {
            "kind": "rate_limited",
            "retryable": True,
            "statusCode": 429,
        },
    }


def test_failure_without_http_status_omits_status_code() -> None:
    result = DeliveryResult(
        DeliveryState.FAILED,
        attempts=2,
        error=DeliveryError(DeliveryErrorKind.TRANSPORT, retryable=True),
    )

    assert delivery_result_to_json(result)["error"] == {
        "kind": "transport",
        "retryable": True,
    }
