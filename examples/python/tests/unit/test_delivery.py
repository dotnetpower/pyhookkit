"""Provider-neutral delivery result tests."""

from collections.abc import Callable

import pytest

from pyhookkit.domain.delivery import (
    DeliveryError,
    DeliveryErrorKind,
    DeliveryResult,
    DeliveryState,
)


def test_delivery_result_accepts_terminal_outcomes() -> None:
    success = DeliveryResult(DeliveryState.SUCCEEDED, attempts=1)
    failure = DeliveryResult(
        DeliveryState.FAILED,
        attempts=2,
        error=DeliveryError(
            DeliveryErrorKind.RATE_LIMITED, retryable=True, status_code=429
        ),
    )

    assert success.error is None
    assert failure.error is not None


@pytest.mark.parametrize(
    "factory",
    [
        lambda: DeliveryResult(DeliveryState.SUCCEEDED, attempts=0),
        lambda: DeliveryResult(
            DeliveryState.SUCCEEDED,
            attempts=1,
            error=DeliveryError(DeliveryErrorKind.TRANSPORT, retryable=True),
        ),
        lambda: DeliveryResult(DeliveryState.FAILED, attempts=1),
    ],
)
def test_delivery_result_rejects_inconsistent_state(
    factory: Callable[[], DeliveryResult],
) -> None:
    with pytest.raises(ValueError):
        factory()
