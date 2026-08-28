"""Teams Hello World Adaptive Card rendering."""

from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.json_types import JsonObject


class TeamsTextRenderer:
    """Render a canonical notification as a Teams Workflow message."""

    def render(self, notification: CanonicalNotification) -> JsonObject:
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": (
                            "http://adaptivecards.io/schemas/adaptive-card.json"
                        ),
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": notification.body,
                                "wrap": True,
                            }
                        ],
                    },
                }
            ],
        }
