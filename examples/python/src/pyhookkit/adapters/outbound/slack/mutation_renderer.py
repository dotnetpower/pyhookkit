"""Slack Web API message mutation payload rendering."""

from pyhookkit.adapters.outbound.slack.message_reference import (
    SlackMessageReference,
)
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.json_types import JsonObject
from pyhookkit.ports.message_renderer import MessageRenderer


class SlackMutationRenderer:
    """Render chat.update and chat.delete request bodies."""

    def __init__(self, message_renderer: MessageRenderer) -> None:
        self._message_renderer = message_renderer

    def render_update(
        self,
        reference: SlackMessageReference,
        notification: CanonicalNotification,
    ) -> JsonObject:
        payload = self._message_renderer.render(notification)
        payload["channel"] = reference.channel_id
        payload["ts"] = reference.message_ts
        return payload

    @staticmethod
    def render_delete(reference: SlackMessageReference) -> JsonObject:
        return {
            "channel": reference.channel_id,
            "ts": reference.message_ts,
        }
