"""Outbound rendering boundary."""

from typing import Protocol

from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.json_types import JsonObject


class MessageRenderer(Protocol):
    """Render one canonical notification into a provider payload."""

    def render(self, notification: CanonicalNotification) -> JsonObject:
        """Return a JSON-compatible provider payload."""
        ...
