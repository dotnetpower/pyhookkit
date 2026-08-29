"""Canonical notification to Slack message rendering."""

from html import escape
from urllib.parse import urlsplit

from pyhookkit.adapters.outbound.slack.identity import (
    SlackIdentityDirectory,
)
from pyhookkit.domain.notification import CanonicalNotification, Severity
from pyhookkit.json_types import JsonObject, JsonValue

_SEVERITY_COLORS = {
    Severity.INFO: "#36C5F0",
    Severity.SUCCESS: "#2EB67D",
    Severity.WARNING: "#ECB22E",
    Severity.ERROR: "#E01E5A",
}


class SlackPayloadLimitError(ValueError):
    """Canonical content exceeds a Slack-specific rendered limit."""


class SlackHeroImageUrlError(ValueError):
    """The Slack presentation hero URL is invalid."""


class SlackMessageRenderer:
    """Render rich canonical notifications for Slack."""

    def __init__(
        self,
        identity_directory: SlackIdentityDirectory | None = None,
        *,
        hero_image_url: str | None = None,
    ) -> None:
        if hero_image_url is not None:
            parsed_url = urlsplit(hero_image_url)
            if parsed_url.scheme != "https" or not parsed_url.netloc:
                raise SlackHeroImageUrlError(
                    "Slack hero image URL must be an absolute HTTPS URL"
                )
        self._identity_directory = identity_directory
        self._hero_image_url = hero_image_url

    def render(self, notification: CanonicalNotification) -> JsonObject:
        blocks: list[JsonValue] = []
        if self._hero_image_url is not None:
            blocks.append(
                {
                    "type": "image",
                    "image_url": self._hero_image_url,
                    "alt_text": "PyHookKit notification presentation",
                }
            )
        if notification.title is not None:
            blocks.append(
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": notification.title,
                    },
                }
            )
        blocks.extend(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": body_chunk,
                },
            }
            for body_chunk in _escaped_text_chunks(notification.body, 3000)
        )
        if notification.facts:
            rendered_facts: list[JsonValue] = [
                _render_fact(fact.key, fact.value) for fact in notification.facts
            ]
            blocks.extend(
                {"type": "section", "fields": fact_chunk}
                for fact_chunk in _list_chunks(rendered_facts, 10)
            )
        if notification.mentions:
            blocks.append(self._render_mentions(notification))
        if notification.image is not None:
            blocks.append(
                {
                    "type": "image",
                    "image_url": notification.image.url,
                    "alt_text": notification.image.alt_text,
                }
            )
        if notification.links:
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": link.label,
                            },
                            "url": link.url,
                            "action_id": f"open_link_{index}",
                        }
                        for index, link in enumerate(notification.links, start=1)
                    ],
                }
            )
        context = self._render_context(notification)
        if context is not None:
            blocks.append(context)

        return {
            "text": _fallback_text(notification),
            "attachments": [
                {
                    "color": _SEVERITY_COLORS[notification.severity],
                    "blocks": blocks,
                }
            ],
        }

    def _render_mentions(self, notification: CanonicalNotification) -> JsonObject:
        if self._identity_directory is None:
            raise ValueError("Slack identity directory is required for mentions")
        rendered = " ".join(
            self._identity_directory.render(mention)
            for mention in notification.mentions
        )
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": rendered,
            },
        }

    @staticmethod
    def _render_context(
        notification: CanonicalNotification,
    ) -> JsonObject | None:
        context: list[JsonValue] = []
        source = notification.metadata.get("source")
        if source is not None:
            context.append(
                {
                    "type": "mrkdwn",
                    "text": f"Source: {_escape_mrkdwn(str(source))}",
                }
            )
        if notification.source_timestamp is not None:
            context.append(
                {
                    "type": "mrkdwn",
                    "text": notification.source_timestamp.isoformat(),
                }
            )
        if not context:
            return None
        return {"type": "context", "elements": context}


def _fallback_text(notification: CanonicalNotification) -> str:
    if notification.title is None:
        return notification.body
    return f"{notification.title}: {notification.body}"


def _escape_mrkdwn(value: str) -> str:
    return escape(value, quote=False)


def _render_fact(key: str, value: str) -> JsonObject:
    text = f"*{_escape_mrkdwn(key)}*\n{_escape_mrkdwn(value)}"
    if len(text) > 2000:
        raise SlackPayloadLimitError(
            "rendered Slack fact must not exceed 2000 characters"
        )
    return {"type": "mrkdwn", "text": text}


def _list_chunks[T](values: list[T], size: int) -> list[list[T]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _escaped_text_chunks(value: str, size: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for character in value:
        escaped_character = _escape_mrkdwn(character)
        if current and current_length + len(escaped_character) > size:
            chunks.append("".join(current))
            current = []
            current_length = 0
        current.append(escaped_character)
        current_length += len(escaped_character)
    if current:
        chunks.append("".join(current))
    return chunks
