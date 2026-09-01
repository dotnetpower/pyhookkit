"""Shared canonical input for the incident alert and acknowledgment pair."""

from pyhookkit.application.scenarios.incident_alert_acknowledgment import (
    build_example_notification,
)
from pyhookkit.domain.notification import CanonicalNotification


def build_notification() -> CanonicalNotification:
    return build_example_notification()
