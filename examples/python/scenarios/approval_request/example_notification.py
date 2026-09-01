"""Shared canonical input for the approval request pair."""

from pyhookkit.application.scenarios.approval_request import (
    build_example_notification,
)
from pyhookkit.domain.notification import CanonicalNotification


def build_notification() -> CanonicalNotification:
    return build_example_notification()
