"""Slack thread reply payload rendering."""

from pyhookkit.adapters.outbound.slack.message_reference import (
    SlackMessageReference,
)
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.json_types import JsonObject
from pyhookkit.ports.message_renderer import MessageRenderer


class SlackThreadRenderer:
    """Add a known Slack parent timestamp to a rendered message."""

    def __init__(self, message_renderer: MessageRenderer) -> None:
        self._message_renderer = message_renderer

    def render(
        self,
        notification: CanonicalNotification,
        parent: SlackMessageReference,
    ) -> JsonObject:
        payload = self._message_renderer.render(notification)
        payload["thread_ts"] = parent.message_ts
        return payload
