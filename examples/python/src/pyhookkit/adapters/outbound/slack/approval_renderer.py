"""Render a canonical notification with Slack approval actions."""

from pyhookkit.adapters.outbound.slack.message_renderer import SlackMessageRenderer
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.json_types import JsonObject, JsonValue


class SlackApprovalRenderer:
    """Add explicit approve and reject actions to a Slack message."""

    def __init__(self, message_renderer: SlackMessageRenderer | None = None) -> None:
        self._message_renderer = message_renderer or SlackMessageRenderer()

    def render(self, notification: CanonicalNotification) -> JsonObject:
        payload = self._message_renderer.render(notification)
        attachments = payload.get("attachments")
        if not isinstance(attachments, list) or not attachments:
            raise ValueError("Slack approval payload requires an attachment")
        attachment = attachments[0]
        if not isinstance(attachment, dict):
            raise ValueError("Slack approval attachment must be an object")
        blocks = attachment.get("blocks")
        if not isinstance(blocks, list):
            raise ValueError("Slack approval attachment requires blocks")
        actions: list[JsonValue] = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve"},
                "style": "primary",
                "action_id": "approval_approve",
                "value": notification.event_id,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Reject"},
                "style": "danger",
                "action_id": "approval_reject",
                "value": notification.event_id,
                "confirm": {
                    "title": {"type": "plain_text", "text": "Reject request?"},
                    "text": {
                        "type": "mrkdwn",
                        "text": "This records a rejection.",
                    },
                    "confirm": {"type": "plain_text", "text": "Reject"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            },
        ]
        blocks.append({"type": "actions", "block_id": "approval", "elements": actions})
        return payload
