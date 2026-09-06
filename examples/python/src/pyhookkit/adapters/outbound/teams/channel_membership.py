"""Microsoft Graph membership provisioning for private Teams channels."""

from typing import cast
from urllib.parse import quote, urlsplit
from uuid import UUID

import httpx

from pyhookkit.adapters.outbound.teams.graph_membership import (
    GraphRequest,
    MicrosoftGraphAccessToken,
    TeamMembershipResult,
    TeamsGraphMembershipError,
)
from pyhookkit.json_types import JsonObject, JsonValue

_GRAPH_ORIGIN = "https://graph.microsoft.com"


class TeamsGraphChannelMembershipProvisioner:
    """Ensure a user is a direct non-owner member of a private channel."""

    def __init__(
        self,
        token: MicrosoftGraphAccessToken,
        *,
        request: GraphRequest = httpx.request,
        timeout_seconds: float = 15.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Microsoft Graph timeout must be positive")
        self._token = token
        self._request = request
        self._timeout_seconds = timeout_seconds

    def ensure_member(
        self,
        team_id: UUID,
        channel_id: str,
        user_id: UUID,
    ) -> TeamMembershipResult:
        """Add a private-channel member only when currently absent."""
        if self.is_member(team_id, channel_id, user_id):
            return TeamMembershipResult(user_id, added=False)
        response = self._send(
            "POST",
            self._members_url(team_id, channel_id),
            payload={
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": [],
                "user@odata.bind": f"{_GRAPH_ORIGIN}/v1.0/users('{user_id}')",
            },
        )
        if response.status_code == 201:
            return TeamMembershipResult(user_id, added=True)
        if response.status_code in {400, 409} and self.is_member(
            team_id,
            channel_id,
            user_id,
        ):
            return TeamMembershipResult(user_id, added=False)
        raise TeamsGraphMembershipError(
            f"Microsoft Graph private channel member creation failed with HTTP "
            f"{response.status_code}"
        )

    def is_member(
        self,
        team_id: UUID,
        channel_id: str,
        user_id: UUID,
    ) -> bool:
        """Return whether a user is a direct private-channel member."""
        next_url: str | None = self._members_url(team_id, channel_id)
        while next_url is not None:
            _validate_graph_url(next_url)
            response = self._send("GET", next_url)
            if response.status_code != 200:
                raise TeamsGraphMembershipError(
                    f"Microsoft Graph private channel member lookup failed with HTTP "
                    f"{response.status_code}"
                )
            payload = _response_object(response)
            raw_members = payload.get("value")
            if not isinstance(raw_members, list):
                raise TeamsGraphMembershipError(
                    "Microsoft Graph private channel member response is malformed"
                )
            for member in cast(list[JsonValue], raw_members):
                if not isinstance(member, dict):
                    raise TeamsGraphMembershipError(
                        "Microsoft Graph private channel member response is malformed"
                    )
                if member.get("userId") == str(user_id):
                    return True
            raw_next_link = payload.get("@odata.nextLink")
            if raw_next_link is not None and not isinstance(raw_next_link, str):
                raise TeamsGraphMembershipError(
                    "Microsoft Graph private channel next link is malformed"
                )
            next_url = raw_next_link
        return False

    def _members_url(self, team_id: UUID, channel_id: str) -> str:
        encoded_channel_id = quote(channel_id, safe="")
        return (
            f"{_GRAPH_ORIGIN}/v1.0/teams/{team_id}/channels/"
            f"{encoded_channel_id}/members"
        )

    def _send(
        self,
        method: str,
        url: str,
        *,
        payload: JsonObject | None = None,
    ) -> httpx.Response:
        try:
            return self._request(
                method,
                url,
                headers={
                    "Authorization": f"Bearer {self._token.value}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise TeamsGraphMembershipError(
                "Microsoft Graph private channel membership request failed"
            ) from error


def _response_object(response: httpx.Response) -> JsonObject:
    try:
        value: object = response.json()
    except ValueError as error:
        raise TeamsGraphMembershipError(
            "Microsoft Graph private channel member response is not JSON"
        ) from error
    if not isinstance(value, dict):
        raise TeamsGraphMembershipError(
            "Microsoft Graph private channel member response must be an object"
        )
    return cast(JsonObject, cast(dict[str, object], value))


def _validate_graph_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "graph.microsoft.com"
        or not parsed.path.startswith("/v1.0/")
    ):
        raise TeamsGraphMembershipError(
            "Microsoft Graph private channel next link has an unexpected origin"
        )
