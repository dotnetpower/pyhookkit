"""Microsoft Graph provisioning for a Teams connection user."""

from dataclasses import dataclass
from typing import Protocol, cast
from urllib.parse import quote, urlsplit
from uuid import UUID

import httpx

from pyhookkit.json_types import JsonObject, JsonValue

_GRAPH_ORIGIN = "https://graph.microsoft.com"


class TeamsGraphMembershipError(RuntimeError):
    """A Team membership check or mutation failed without exposing its body."""


class GraphRequest(Protocol):
    """HTTP request callable used by the Graph adapter."""

    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: JsonObject | None,
        timeout: float,
    ) -> httpx.Response:
        """Send one Microsoft Graph request."""
        ...


@dataclass(frozen=True, slots=True, repr=False)
class MicrosoftGraphAccessToken:
    """A redacted Microsoft Graph bearer token."""

    value: str

    def __post_init__(self) -> None:
        if len(self.value) < 16:
            raise ValueError("Microsoft Graph access token is invalid")

    def __repr__(self) -> str:
        return "MicrosoftGraphAccessToken(value=<redacted>)"


@dataclass(frozen=True, slots=True)
class TeamMembershipResult:
    """The idempotent result of ensuring one non-owner Team member."""

    user_id: UUID
    added: bool


class TeamsGraphMembershipProvisioner:
    """Ensure the Teams connector identity belongs to a target Team."""

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
        user: str,
    ) -> TeamMembershipResult:
        """Add a standard Team member only when it is currently absent."""
        user_id = self._resolve_user_id(user)
        if self._is_member(team_id, user_id):
            return TeamMembershipResult(user_id, added=False)

        response = self._send(
            "POST",
            f"{_GRAPH_ORIGIN}/v1.0/teams/{team_id}/members",
            payload={
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": [],
                "user@odata.bind": (f"{_GRAPH_ORIGIN}/v1.0/users('{user_id}')"),
            },
        )
        if response.status_code == 201:
            return TeamMembershipResult(user_id, added=True)
        if response.status_code == 409 and self._is_member(team_id, user_id):
            return TeamMembershipResult(user_id, added=False)
        raise TeamsGraphMembershipError(
            f"Microsoft Graph member creation failed with HTTP {response.status_code}"
        )

    def _resolve_user_id(self, user: str) -> UUID:
        normalized = user.strip()
        if not normalized:
            raise ValueError("Teams connection user must not be blank")
        try:
            return UUID(normalized)
        except ValueError:
            pass

        response = self._send(
            "GET",
            f"{_GRAPH_ORIGIN}/v1.0/users/{quote(normalized, safe='')}?$select=id",
        )
        if response.status_code != 200:
            raise TeamsGraphMembershipError(
                f"Microsoft Graph user lookup failed with HTTP {response.status_code}"
            )
        payload = _response_object(response, "user lookup")
        raw_user_id = payload.get("id")
        if not isinstance(raw_user_id, str):
            raise TeamsGraphMembershipError(
                "Microsoft Graph user lookup response is malformed"
            )
        try:
            return UUID(raw_user_id)
        except ValueError as error:
            raise TeamsGraphMembershipError(
                "Microsoft Graph user lookup returned an invalid user ID"
            ) from error

    def _is_member(self, team_id: UUID, user_id: UUID) -> bool:
        next_url: str | None = (
            f"{_GRAPH_ORIGIN}/v1.0/teams/{team_id}/members?$select=id,userId,roles"
        )
        while next_url is not None:
            _validate_graph_url(next_url)
            response = self._send("GET", next_url)
            if response.status_code != 200:
                raise TeamsGraphMembershipError(
                    f"Microsoft Graph member lookup failed with HTTP "
                    f"{response.status_code}"
                )
            payload = _response_object(response, "member lookup")
            raw_members = payload.get("value")
            if not isinstance(raw_members, list):
                raise TeamsGraphMembershipError(
                    "Microsoft Graph member lookup response is malformed"
                )
            for member in cast(list[JsonValue], raw_members):
                if not isinstance(member, dict):
                    raise TeamsGraphMembershipError(
                        "Microsoft Graph member lookup response is malformed"
                    )
                if member.get("userId") == str(user_id):
                    return True
            raw_next_link = payload.get("@odata.nextLink")
            if raw_next_link is not None and not isinstance(raw_next_link, str):
                raise TeamsGraphMembershipError(
                    "Microsoft Graph member next link is malformed"
                )
            next_url = raw_next_link
        return False

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
                "Microsoft Graph membership request failed"
            ) from error


def _response_object(response: httpx.Response, operation: str) -> JsonObject:
    try:
        value: object = response.json()
    except ValueError as error:
        raise TeamsGraphMembershipError(
            f"Microsoft Graph {operation} response is not JSON"
        ) from error
    if not isinstance(value, dict):
        raise TeamsGraphMembershipError(
            f"Microsoft Graph {operation} response must be an object"
        )
    mapping = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in mapping):
        raise TeamsGraphMembershipError(
            f"Microsoft Graph {operation} response has invalid keys"
        )
    return cast(JsonObject, mapping)


def _validate_graph_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "graph.microsoft.com"
        or not parsed.path.startswith("/v1.0/")
    ):
        raise TeamsGraphMembershipError(
            "Microsoft Graph member next link has an unexpected origin"
        )
