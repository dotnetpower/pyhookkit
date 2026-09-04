"""Central routing value object validation tests."""

from collections.abc import Callable

import pytest

from pyhookkit.domain.delivery import DeliveryErrorKind
from pyhookkit.domain.routing import (
    NotificationState,
    RoutedNotificationStatus,
    TargetDeliveryState,
    TargetDeliveryStatus,
)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: TargetDeliveryStatus(" ", TargetDeliveryState.QUEUED),
        lambda: TargetDeliveryStatus(
            "target",
            TargetDeliveryState.QUEUED,
            attempts=-1,
        ),
        lambda: TargetDeliveryStatus("target", TargetDeliveryState.FAILED),
        lambda: TargetDeliveryStatus(
            "target",
            TargetDeliveryState.SUCCEEDED,
            error_kind=DeliveryErrorKind.TRANSPORT,
        ),
        lambda: RoutedNotificationStatus(
            " ",
            "event",
            NotificationState.QUEUED,
            (TargetDeliveryStatus("target", TargetDeliveryState.QUEUED),),
        ),
        lambda: RoutedNotificationStatus(
            "notification",
            " ",
            NotificationState.QUEUED,
            (TargetDeliveryStatus("target", TargetDeliveryState.QUEUED),),
        ),
        lambda: RoutedNotificationStatus(
            "notification",
            "event",
            NotificationState.QUEUED,
            (),
        ),
    ],
)
def test_routing_values_reject_inconsistent_state(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ValueError):
        factory()
