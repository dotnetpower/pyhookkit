"""Build a dynamically routed Microsoft Teams Workflow request."""

from pyhookkit.adapters.outbound.teams.channel_link import TeamsChannelLink
from pyhookkit.json_types import JsonObject


class TeamsWorkflowRequestError(ValueError):
    """A Teams envelope cannot be adapted to the routed Workflow contract."""


def build_teams_workflow_request(
    envelope: JsonObject,
    channel_link: TeamsChannelLink,
) -> JsonObject:
    """Add an allowed channel link without changing the rendered message."""
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
    if "channelLink" in envelope:
        raise TeamsWorkflowRequestError("Teams envelope already contains channelLink")
    return {
        **envelope,
        "channelLink": channel_link.value,
        "teamId": str(channel_link.team_id),
        "channelId": channel_link.channel_id,
    }
