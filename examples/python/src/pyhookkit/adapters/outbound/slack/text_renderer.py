"""Slack Hello World text rendering."""

from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.json_types import JsonObject


class SlackTextRenderer:
    """Render a canonical notification as a Slack text message."""

    def render(self, notification: CanonicalNotification) -> JsonObject:
        return {"text": notification.body}
