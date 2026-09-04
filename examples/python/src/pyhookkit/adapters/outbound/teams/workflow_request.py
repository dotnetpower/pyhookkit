"""Build a dynamically routed Microsoft Teams Workflow request."""

from re import fullmatch
from uuid import UUID

from pyhookkit.json_types import JsonObject


class TeamsWorkflowRequestError(ValueError):
    """A Teams envelope cannot be adapted to the routed Workflow contract."""


def build_teams_workflow_request(
    envelope: JsonObject,
    *,
    team_id: UUID,
    channel_id: str,
) -> JsonObject:
    """Add validated routing IDs to a Teams webhook message envelope."""
    if envelope.get("type") != "message":
        raise TeamsWorkflowRequestError("Teams envelope type must be message")
    attachments = envelope.get("attachments")
    if not isinstance(attachments, list) or len(attachments) != 1:
        raise TeamsWorkflowRequestError(
            "Teams envelope must contain exactly one attachment"
        )
    attachment = attachments[0]
    if (
        not isinstance(attachment, dict)
        or attachment.get("contentType") != "application/vnd.microsoft.card.adaptive"
        or not isinstance(attachment.get("content"), dict)
    ):
        raise TeamsWorkflowRequestError(
            "Teams envelope attachment must contain Adaptive Card content"
        )
    content = attachment["content"]
    if not isinstance(content, dict):
        raise TeamsWorkflowRequestError(
            "Teams envelope attachment must contain Adaptive Card content"
        )
    if content.get("type") != "AdaptiveCard":
        raise TeamsWorkflowRequestError("Teams attachment content must be AdaptiveCard")
    if fullmatch(r"19:[A-Za-z0-9_-]+@thread\.(?:tacv2|skype)", channel_id) is None:
        raise TeamsWorkflowRequestError("Teams channel ID is invalid")
    if "teamId" in envelope or "channelId" in envelope:
        raise TeamsWorkflowRequestError(
            "Teams envelope cannot contain routing identifiers"
        )
    return {
        **envelope,
        "teamId": str(team_id),
        "channelId": channel_id,
    }
