"""Slack identity lookup and mention formatting."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from pyhookkit.domain.notification import Mention, MentionKind

_USER_ID = re.compile(r"^[UW][A-Z0-9]+$")
_GROUP_ID = re.compile(r"^S[A-Z0-9]+$")


class SlackIdentityNotFoundError(ValueError):
    """A logical mention alias has no Slack identity mapping."""


@dataclass(frozen=True, slots=True)
class SlackIdentity:
    """A provider-owned Slack identity."""

    kind: MentionKind
    identifier: str

    def __post_init__(self) -> None:
        pattern = _USER_ID if self.kind is MentionKind.USER else _GROUP_ID
        if not pattern.fullmatch(self.identifier):
            raise ValueError(f"invalid Slack {self.kind.value} identifier")


class SlackIdentityDirectory:
    """Resolve logical aliases to Slack mention syntax."""

    def __init__(self, identities: Mapping[str, SlackIdentity]) -> None:
        self._identities = dict(identities)

    def render(self, mention: Mention) -> str:
        try:
            identity = self._identities[mention.alias]
        except KeyError as error:
            raise SlackIdentityNotFoundError(
                f"Slack identity is not configured for alias: {mention.alias}"
            ) from error
        if identity.kind is not mention.kind:
            raise SlackIdentityNotFoundError(
                f"Slack identity kind does not match alias: {mention.alias}"
            )
        if identity.kind is MentionKind.USER:
            return f"<@{identity.identifier}>"
        return f"<!subteam^{identity.identifier}>"
