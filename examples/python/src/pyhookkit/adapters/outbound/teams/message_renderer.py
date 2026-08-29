"""Canonical notification to rich Microsoft Teams Adaptive Card rendering."""

from enum import StrEnum
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


class TeamsGroupMentionPolicy(StrEnum):
    """How a Teams card represents canonical group mentions."""

    CONFIGURATION_NOTICE = "configuration_notice"
    OMIT = "omit"


class TeamsActionPresentation(StrEnum):
    """How canonical links are presented in a Teams card."""

    STANDARD = "standard"
    EDGE_TO_EDGE = "edge_to_edge"


class TeamsMessageRenderer:
    """Render polished canonical notifications for a Teams Workflow."""

    def __init__(
        self,
        identity_directory: TeamsIdentityDirectory | None = None,
        *,
        hero_image_url: str | None = _DEFAULT_HERO_URL,
        capability_notice: str | None = None,
        group_mention_policy: TeamsGroupMentionPolicy = (
            TeamsGroupMentionPolicy.CONFIGURATION_NOTICE
        ),
        action_presentation: TeamsActionPresentation = (
            TeamsActionPresentation.STANDARD
        ),
        show_body_in_card: bool = True,
        show_hero_label: bool = True,
        hero_min_height: int = 180,
    ) -> None:
        if hero_image_url is not None:
            parsed_url = urlsplit(hero_image_url)
            if parsed_url.scheme != "https" or not parsed_url.netloc:
                raise TeamsHeroImageUrlError(
                    "Teams hero image URL must be an absolute HTTPS URL"
                )
        if capability_notice is not None and not capability_notice.strip():
            raise ValueError("Teams capability notice must not be blank")
        if hero_min_height < 1:
            raise ValueError("Teams hero minimum height must be positive")
        self._identity_directory = identity_directory
        self._hero_image_url = hero_image_url
        self._capability_notice = capability_notice
        self._group_mention_policy = group_mention_policy
        self._action_presentation = action_presentation
        self._show_body_in_card = show_body_in_card
        self._show_hero_label = show_hero_label
        self._hero_min_height = hero_min_height

    def render(self, notification: CanonicalNotification) -> JsonObject:
        body = self._render_header(notification)
        if self._show_body_in_card:
            body.append(self._render_body(notification))
        if self._capability_notice is not None:
            body.append(self._render_capability_notice(notification))
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
        if (
            notification.links
            and self._action_presentation is TeamsActionPresentation.EDGE_TO_EDGE
        ):
            body.append(self._render_edge_to_edge_actions(notification))

        fallback_text = _fallback_text(notification)
        if self._capability_notice is not None:
            fallback_text = (
                f"{fallback_text} Teams Workflow capability: {self._capability_notice}"
            )
            if notification.thread_key is not None:
                fallback_text = (
                    f"{fallback_text} Requested thread key: {notification.thread_key}."
                )

        card: JsonObject = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "fallbackText": fallback_text,
            "speak": fallback_text,
            "body": body,
        }
        if (
            notification.links
            and self._action_presentation is TeamsActionPresentation.STANDARD
        ):
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
        header: list[JsonValue] = []
        if self._hero_image_url is not None:
            hero: JsonObject = {
                "type": "Container",
                "backgroundImage": {
                    "url": self._hero_image_url,
                    "fillMode": "Cover",
                    "horizontalAlignment": "Center",
                    "verticalAlignment": "Center",
                },
                "bleed": True,
                "minHeight": f"{self._hero_min_height}px",
            }
            if self._show_hero_label:
                hero["verticalContentAlignment"] = "Bottom"
                hero["items"] = [
                    {
                        "type": "Container",
                        "style": "accent",
                        "bleed": True,
                        "spacing": "None",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "PYHOOKKIT NOTIFICATION",
                                "wrap": True,
                                "weight": "Bolder",
                                "horizontalAlignment": "Center",
                                "spacing": "None",
                            }
                        ],
                    }
                ]
            header.append(hero)
        header.extend(
            [
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
        )
        return header

    @staticmethod
    def _render_edge_to_edge_actions(
        notification: CanonicalNotification,
    ) -> JsonObject:
        return {
            "type": "Container",
            "style": "accent",
            "bleed": True,
            "spacing": "Medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "Continue to the investigation details",
                    "wrap": True,
                    "weight": "Bolder",
                    "horizontalAlignment": "Center",
                    "spacing": "None",
                },
                {
                    "type": "ActionSet",
                    "horizontalAlignment": "Center",
                    "spacing": "Small",
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": link.label,
                            "url": link.url,
                        }
                        for link in notification.links
                    ],
                },
            ],
        }

    def _render_capability_notice(
        self,
        notification: CanonicalNotification,
    ) -> JsonObject:
        items: list[JsonValue] = [
            {
                "type": "TextBlock",
                "text": "TEAMS WORKFLOW CAPABILITY",
                "weight": "Bolder",
                "size": "Small",
                "color": "Warning",
                "spacing": "None",
            },
            {
                "type": "TextBlock",
                "text": self._capability_notice,
                "wrap": True,
                "spacing": "Small",
            },
        ]
        if notification.thread_key is not None:
            items.append(
                {
                    "type": "TextBlock",
                    "text": f"Requested thread key · {notification.thread_key}",
                    "wrap": True,
                    "isSubtle": True,
                    "size": "Small",
                    "spacing": "Small",
                }
            )
        return {
            "type": "Container",
            "style": "accent",
            "spacing": "Medium",
            "items": items,
        }

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
                if (
                    self._group_mention_policy
                    is TeamsGroupMentionPolicy.CONFIGURATION_NOTICE
                ):
                    rendered.append(
                        f"{mention.alias} (additional Graph member-expansion "
                        "configuration required)"
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
