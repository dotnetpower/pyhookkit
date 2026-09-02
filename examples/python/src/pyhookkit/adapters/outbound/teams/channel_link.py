"""Validated Microsoft Teams channel links for Workflow routing."""

from dataclasses import dataclass, field
from re import fullmatch
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import UUID


class TeamsChannelLinkError(ValueError):
    """A Teams channel link cannot identify a supported destination."""


@dataclass(frozen=True, slots=True, repr=False)
class TeamsChannelLink:
    """Provider routing identifiers extracted from a Teams channel link."""

    value: str
    team_id: UUID = field(init=False)
    channel_id: str = field(init=False)
    tenant_id: UUID = field(init=False)

    def __post_init__(self) -> None:
        parsed = urlsplit(self.value)
        if (
            parsed.scheme != "https"
            or parsed.netloc.lower() != "teams.microsoft.com"
            or parsed.fragment
        ):
            raise TeamsChannelLinkError(
                "Teams channel link must use https://teams.microsoft.com"
            )

        path_parts = parsed.path.split("/")
        if len(path_parts) != 5 or path_parts[1:3] != ["l", "channel"]:
            raise TeamsChannelLinkError("Teams channel link path is invalid")
        channel_id = unquote(path_parts[3])
        channel_name = unquote(path_parts[4]).strip()
        if (
            fullmatch(r"19:[A-Za-z0-9_-]+@thread\.(?:tacv2|skype)", channel_id) is None
            or not channel_name
        ):
            raise TeamsChannelLinkError(
                "Teams channel link must contain a channel ID and name"
            )

        try:
            query = parse_qs(parsed.query, strict_parsing=True)
        except ValueError as error:
            raise TeamsChannelLinkError(
                "Teams channel link query is invalid"
            ) from error
        team_id = _single_uuid(query, "groupId")
        tenant_id = _single_uuid(query, "tenantId")
        object.__setattr__(self, "team_id", team_id)
        object.__setattr__(self, "channel_id", channel_id)
        object.__setattr__(self, "tenant_id", tenant_id)

    def __repr__(self) -> str:
        return "TeamsChannelLink(value=<redacted>)"


def _single_uuid(query: dict[str, list[str]], name: str) -> UUID:
    values = query.get(name, [])
    if len(values) != 1:
        raise TeamsChannelLinkError(f"Teams channel link requires one {name}")
    try:
        return UUID(values[0])
    except ValueError as error:
        raise TeamsChannelLinkError(
            f"Teams channel link {name} must be a GUID"
        ) from error
