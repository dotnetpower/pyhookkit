"""Microsoft Teams identity lookup and Adaptive Card mention entities."""

from collections.abc import Mapping
from dataclasses import dataclass

from pyhookkit.domain.notification import Mention
from pyhookkit.json_types import JsonObject


class TeamsIdentityNotFoundError(ValueError):
    """A logical mention alias has no Teams identity mapping."""


@dataclass(frozen=True, slots=True)
class TeamsIdentity:
    """A provider-owned Teams user identity."""

    identifier: str
    display_name: str

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("Teams identity identifier must not be blank")
        if not self.display_name.strip():
            raise ValueError("Teams identity display name must not be blank")


class TeamsIdentityDirectory:
    """Resolve logical aliases to Teams Adaptive Card user mentions."""

    def __init__(self, identities: Mapping[str, TeamsIdentity]) -> None:
        self._identities = dict(identities)

    def render_user(self, mention: Mention) -> tuple[str, JsonObject]:
        try:
            identity = self._identities[mention.alias]
        except KeyError as error:
            raise TeamsIdentityNotFoundError(
                f"Teams identity is not configured for alias: {mention.alias}"
            ) from error
        text = f"<at>{identity.display_name}</at>"
        return (
            text,
            {
                "type": "mention",
                "text": text,
                "mentioned": {
                    "id": identity.identifier,
                    "name": identity.display_name,
                },
            },
        )
