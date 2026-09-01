"""Shared canonical input for the deployment result pair."""

from pyhookkit.application.scenarios.deployment_result import (
    build_example_notification,
)
from pyhookkit.domain.notification import CanonicalNotification


def build_notification() -> CanonicalNotification:
    return build_example_notification()
