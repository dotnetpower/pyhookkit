"""Canonical notification to rich Microsoft Teams Adaptive Card rendering."""

from urllib.parse import urlsplit

from pyhookkit.adapters.outbound.teams.identity import TeamsIdentityDirectory
from pyhookkit.domain.notification import (
    CanonicalNotification,
    MentionKind,
    Severity,
)
from pyhookkit.json_types import JsonObject, JsonValue

_SEVERITY_PRESENTATION = {
    Severity.INFO: ("INFORMATION", "Accent"),
    Severity.SUCCESS: ("SUCCESS", "Good"),
    Severity.WARNING: ("ATTENTION", "Warning"),
    Severity.ERROR: ("CRITICAL", "Attention"),
}
_DEFAULT_HERO_URL = (
    "https://assets.pyhookkit.example/samples/editorial/assets/editorialHero.png"
)


class TeamsHeroImageUrlError(ValueError):
    """The Teams presentation hero URL is invalid."""


class TeamsMessageRenderer:
    """Render polished canonical notifications for a Teams Workflow."""

    def __init__(
        self,
        identity_directory: TeamsIdentityDirectory | None = None,
        *,
        hero_image_url: str = _DEFAULT_HERO_URL,
    ) -> None:
        parsed_url = urlsplit(hero_image_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise TeamsHeroImageUrlError(
                "Teams hero image URL must be an absolute HTTPS URL"
            )
        self._identity_directory = identity_directory
        self._hero_image_url = hero_image_url

    def render(self, notification: CanonicalNotification) -> JsonObject:
        body = self._render_header(notification)
        body.append(self._render_body(notification))
        if notification.facts:
            body.append(self._render_facts(notification))

        mentions, entities = self._render_mentions(notification)
        if mentions:
            body.append(
                {
                    "type": "Container",
                    "style": "accent",
                    "spacing": "Medium",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": " ".join(mentions),
                            "wrap": True,
                            "weight": "Bolder",
                            "color": "Accent",
                            "horizontalAlignment": "Center",
                            "spacing": "None",
                        }
                    ],
                }
            )
        if notification.image is not None:
            body.append(
                {
                    "type": "Container",
                    "separator": True,
                    "spacing": "Medium",
                    "items": [
                        {
                            "type": "Image",
                            "url": notification.image.url,
                            "altText": notification.image.alt_text,
                            "size": "Stretch",
                            "horizontalAlignment": "Center",
                        },
                        {
                            "type": "TextBlock",
                            "text": notification.image.alt_text,
                            "wrap": True,
                            "isSubtle": True,
                            "size": "Small",
                            "horizontalAlignment": "Center",
                            "spacing": "Small",
                        },
                    ],
                }
            )

        context = self._render_context(notification)
        if context is not None:
            body.append(context)

        card: JsonObject = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "fallbackText": _fallback_text(notification),
            "speak": _fallback_text(notification),
            "body": body,
        }
        if notification.links:
            card["actions"] = [
                {
                    "type": "Action.OpenUrl",
                    "title": link.label,
                    "url": link.url,
                }
                for link in notification.links
            ]
        if entities:
            card["msteams"] = {"entities": entities}
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": card,
                }
            ],
        }

    def _render_header(
        self,
        notification: CanonicalNotification,
    ) -> list[JsonValue]:
        label, color = _SEVERITY_PRESENTATION[notification.severity]
        title = notification.title or "Notification"
        return [
            {
                "type": "Container",
                "backgroundImage": {
                    "url": self._hero_image_url,
                    "fillMode": "Cover",
                    "horizontalAlignment": "Center",
                    "verticalAlignment": "Center",
                },
                "bleed": True,
                "minHeight": "180px",
                "verticalContentAlignment": "Bottom",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "PYHOOKKIT NOTIFICATION",
                        "wrap": True,
                        "weight": "Bolder",
                        "color": "Dark",
                    }
                ],
            },
            {
                "type": "TextBlock",
                "text": label,
                "weight": "Bolder",
                "size": "Small",
                "color": color,
                "horizontalAlignment": "Center",
                "spacing": "Medium",
            },
            {
                "type": "TextBlock",
                "text": title,
                "weight": "Bolder",
                "size": "ExtraLarge",
                "wrap": True,
                "horizontalAlignment": "Center",
                "spacing": "Small",
            },
            {
                "type": "TextBlock",
                "text": f"PyHookKit · {notification.route}",
                "isSubtle": True,
                "size": "Small",
                "horizontalAlignment": "Center",
                "spacing": "Small",
            },
        ]

    @staticmethod
    def _render_body(notification: CanonicalNotification) -> JsonObject:
        return {
            "type": "Container",
            "spacing": "Medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": notification.body,
                    "wrap": True,
                    "horizontalAlignment": "Center",
                    "isSubtle": True,
                    "size": "Medium",
                    "spacing": "None",
                }
            ],
        }

    @staticmethod
    def _render_facts(notification: CanonicalNotification) -> JsonObject:
        rows: list[JsonValue] = []
        for index in range(0, len(notification.facts), 2):
            columns: list[JsonValue] = []
            for fact in notification.facts[index : index + 2]:
                columns.append(
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": fact.key.upper(),
                                "isSubtle": True,
                                "size": "Small",
                                "weight": "Bolder",
                                "spacing": "None",
                            },
                            {
                                "type": "TextBlock",
                                "text": fact.value,
                                "wrap": True,
                                "weight": "Bolder",
                                "spacing": "Small",
                            },
                        ],
                    }
                )
            if len(columns) == 1:
                columns.append({"type": "Column", "width": "stretch", "items": []})
            rows.append(
                {
                    "type": "ColumnSet",
                    "spacing": "Medium" if rows else "None",
                    "columns": columns,
                }
            )
        return {
            "type": "Container",
            "separator": True,
            "spacing": "Medium",
            "items": rows,
        }

    def _render_mentions(
        self,
        notification: CanonicalNotification,
    ) -> tuple[list[str], list[JsonValue]]:
        rendered: list[str] = []
        entities: list[JsonValue] = []
        for mention in notification.mentions:
            if mention.kind is MentionKind.GROUP:
                rendered.append(
                    f"{mention.alias} (Teams Workflow group notification unavailable)"
                )
                continue
            if self._identity_directory is None:
                raise ValueError(
                    "Teams identity directory is required for user mentions"
                )
            text, entity = self._identity_directory.render_user(mention)
            rendered.append(text)
            entities.append(entity)
        return rendered, entities

    @staticmethod
    def _render_context(
        notification: CanonicalNotification,
    ) -> JsonObject | None:
        columns: list[JsonValue] = []
        source = notification.metadata.get("source")
        if source is not None:
            columns.append(
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": source,
                            "wrap": True,
                            "isSubtle": True,
                            "size": "Small",
                        }
                    ],
                }
            )
        if notification.source_timestamp is not None:
            columns.append(
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": notification.source_timestamp.isoformat(),
                            "wrap": True,
                            "isSubtle": True,
                            "size": "Small",
                            "horizontalAlignment": "Right",
                        }
                    ],
                }
            )
        if not columns:
            return None
        return {
            "type": "ColumnSet",
            "separator": True,
            "spacing": "Medium",
            "columns": columns,
        }


def _fallback_text(notification: CanonicalNotification) -> str:
    if notification.title is None:
        return notification.body
    return f"{notification.title}: {notification.body}"
