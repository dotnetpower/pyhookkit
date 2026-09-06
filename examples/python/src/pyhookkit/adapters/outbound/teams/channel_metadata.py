"""Microsoft Graph metadata lookup for registered Teams channels."""

from enum import StrEnum
from typing import cast
from urllib.parse import quote
from uuid import UUID

import httpx

from pyhookkit.adapters.outbound.teams.graph_membership import (
    GraphRequest,
    MicrosoftGraphAccessToken,
    TeamsGraphMembershipError,
)

_GRAPH_ORIGIN = "https://graph.microsoft.com"


class TeamsChannelMembershipType(StrEnum):
    """Supported Microsoft Teams channel membership models."""

    STANDARD = "standard"
    PRIVATE = "private"
    SHARED = "shared"


class TeamsGraphChannelInspector:
    """Read one channel's membership model without exposing its metadata."""

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

    def membership_type(
        self,
        team_id: UUID,
        channel_id: str,
    ) -> TeamsChannelMembershipType:
        """Return whether a Teams channel is standard, private, or shared."""
        encoded_channel_id = quote(channel_id, safe="")
        try:
            response = self._request(
                "GET",
                (
                    f"{_GRAPH_ORIGIN}/v1.0/teams/{team_id}/channels/"
                    f"{encoded_channel_id}?$select=membershipType"
                ),
                headers={
                    "Authorization": f"Bearer {self._token.value}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=None,
                timeout=self._timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise TeamsGraphMembershipError(
                "Microsoft Graph channel metadata request failed"
            ) from error
        if response.status_code != 200:
            raise TeamsGraphMembershipError(
                f"Microsoft Graph channel metadata lookup failed with HTTP "
                f"{response.status_code}"
            )
        try:
            value: object = response.json()
        except ValueError as error:
            raise TeamsGraphMembershipError(
                "Microsoft Graph channel metadata response is not JSON"
            ) from error
        if not isinstance(value, dict):
            raise TeamsGraphMembershipError(
                "Microsoft Graph channel metadata response must be an object"
            )
        response_object = cast(dict[str, object], value)
        raw_membership_type = response_object.get("membershipType")
        if not isinstance(raw_membership_type, str):
            raise TeamsGraphMembershipError(
                "Microsoft Graph channel metadata response is malformed"
            )
        try:
            return TeamsChannelMembershipType(raw_membership_type)
        except ValueError as error:
            raise TeamsGraphMembershipError(
                "Microsoft Graph channel membership type is unsupported"
            ) from error
