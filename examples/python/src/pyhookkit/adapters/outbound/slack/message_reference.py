"""Slack message references used by reply and mutation adapters."""

import re
from dataclasses import dataclass

_CHANNEL_ID = re.compile(r"^[CG][A-Z0-9]+$")
_MESSAGE_TS = re.compile(r"^[0-9]{10,}\.[0-9]{6}$")


@dataclass(frozen=True, slots=True)
class SlackMessageReference:
    """Provider-owned coordinates of an existing Slack message."""

    channel_id: str
    message_ts: str

    def __post_init__(self) -> None:
        if not _CHANNEL_ID.fullmatch(self.channel_id):
            raise ValueError("invalid Slack channel identifier")
        if not _MESSAGE_TS.fullmatch(self.message_ts):
            raise ValueError("invalid Slack message timestamp")
