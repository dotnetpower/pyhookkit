"""Explicit policy for Slack channel and broad-audience references."""

import re
from enum import StrEnum

_CHANNEL_ID = re.compile(r"^[CG][A-Z0-9]+$")


class SlackBroadcastAudience(StrEnum):
    HERE = "here"
    CHANNEL = "channel"
    EVERYONE = "everyone"


class SlackBroadcastNotAllowedError(PermissionError):
    """A broad Slack mention was not explicitly authorized."""


def render_slack_channel_link(channel_id: str) -> str:
    if not _CHANNEL_ID.fullmatch(channel_id):
        raise ValueError("invalid Slack channel identifier")
    return f"<#{channel_id}>"


def render_slack_broadcast(
    audience: SlackBroadcastAudience,
    *,
    allowed: frozenset[SlackBroadcastAudience],
) -> str:
    if audience not in allowed:
        raise SlackBroadcastNotAllowedError(
            f"Slack {audience.value} broadcast is not allowed"
        )
    return f"<!{audience.value}>"
