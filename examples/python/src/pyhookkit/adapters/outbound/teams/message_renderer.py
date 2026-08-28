"""Canonical notification to rich Microsoft Teams Adaptive Card rendering."""

from pyhookkit.adapters.outbound.teams.identity import TeamsIdentityDirectory
from pyhookkit.domain.notification import (
    CanonicalNotification,
    MentionKind,
    Severity,
)
from pyhookkit.json_types import JsonObject, JsonValue

_SEVERITY_PRESENTATION = {
    Severity.INFO: ("💡", "INFO", "Accent"),
    Severity.SUCCESS: ("✅", "SUCCESS", "Good"),
    Severity.WARNING: ("⚠️", "ATTENTION", "Warning"),
    Severity.ERROR: ("🚨", "CRITICAL", "Attention"),
}


class TeamsMessageRenderer:
    """Render polished canonical notifications for a Teams Workflow."""

    def __init__(
        self,
        identity_directory: TeamsIdentityDirectory | None = None,
    ) -> None:
        self._identity_directory = identity_directory

    def render(self, notification: CanonicalNotification) -> JsonObject:
        body: list[JsonValue] = [self._render_header(notification)]
        body.append(
            {
                "type": "Container",
                "spacing": "Medium",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": notification.body,
                        "wrap": True,
                        "spacing": "None",
                    }
                ],
            }
        )
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
                            "text": f"👥  {' '.join(mentions)}",
                            "wrap": True,
                            "weight": "Bolder",
                            "spacing": "None",
                        }
                    ],
                }
            )
        if notification.image is not None:
            body.append(
                {
                    "type": "Container",
                    "style": "emphasis",
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
                    "title": f"↗  {link.label}",
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

    @staticmethod
    def _render_header(notification: CanonicalNotification) -> JsonObject:
        emoji, label, color = _SEVERITY_PRESENTATION[notification.severity]
        title = notification.title or "Notification"
        return {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": [
                {
                    "type": "ColumnSet",
                    "spacing": "None",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "auto",
                            "verticalContentAlignment": "Center",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": emoji,
                                    "size": "ExtraLarge",
                                    "spacing": "None",
                                }
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": label,
                                    "weight": "Bolder",
                                    "size": "Small",
                                    "color": color,
                                    "spacing": "None",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": title,
                                    "weight": "Bolder",
                                    "size": "Large",
                                    "wrap": True,
                                    "spacing": "Small",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"PyHookKit  •  {notification.route}",
                                    "isSubtle": True,
                                    "size": "Small",
                                    "spacing": "Small",
                                },
                            ],
                        },
                    ],
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
            "style": "emphasis",
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
                            "text": f"🔗  {source}",
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
                            "text": (
                                f"🕒  {notification.source_timestamp.isoformat()}"
                            ),
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
