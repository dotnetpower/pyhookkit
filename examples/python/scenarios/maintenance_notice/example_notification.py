"""Shared canonical input for the maintenance notice pair."""

from pyhookkit.application.scenarios.maintenance_notice import (
    build_example_notification,
)
from pyhookkit.domain.notification import CanonicalNotification


def build_notification() -> CanonicalNotification:
    return build_example_notification()
