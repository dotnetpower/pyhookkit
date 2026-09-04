"""Microsoft Graph application token acquisition."""

import base64
import binascii
import json
from dataclasses import dataclass
from typing import Protocol, cast
from uuid import UUID

import httpx

from pyhookkit.adapters.outbound.teams.graph_membership import (
    MicrosoftGraphAccessToken,
)
from pyhookkit.json_types import JsonObject

_MEMBERSHIP_ROLES = frozenset(
    {
        "GroupMember.ReadWrite.All",
        "Group.ReadWrite.All",
    }
)


class MicrosoftGraphTokenError(RuntimeError):
    """An app-only Graph token could not be acquired or validated."""


class TokenRequest(Protocol):
    """HTTP form request used by the client-credentials adapter."""

    def __call__(
        self,
        url: str,
        *,
        data: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        """Send one OAuth token request."""
        ...


@dataclass(frozen=True, slots=True, repr=False)
class TeamsNotifyAppCredentials:
    """A redacted single-tenant client credential."""

    tenant_id: UUID
    client_id: UUID
    client_secret: str

    def __post_init__(self) -> None:
        if len(self.client_secret) < 16:
            raise ValueError("TeamsNotifyApp client secret is invalid")

    def __repr__(self) -> str:
        return (
            "TeamsNotifyAppCredentials("
            f"tenant_id={self.tenant_id!r}, "
            f"client_id={self.client_id!r}, "
            "client_secret=<redacted>)"
        )


class MicrosoftGraphClientCredentialsTokenProvider:
    """Acquire and validate a short-lived TeamsNotifyApp Graph token."""

    def __init__(
        self,
        credentials: TeamsNotifyAppCredentials,
        *,
        post: TokenRequest = httpx.post,
        timeout_seconds: float = 15.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Microsoft Graph token timeout must be positive")
        self._credentials = credentials
        self._post = post
        self._timeout_seconds = timeout_seconds

    def token(self) -> MicrosoftGraphAccessToken:
        """Return an app-only token with the required membership role."""
        try:
            response = self._post(
                (
                    "https://login.microsoftonline.com/"
                    f"{self._credentials.tenant_id}/oauth2/v2.0/token"
                ),
                data={
                    "client_id": str(self._credentials.client_id),
                    "client_secret": self._credentials.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
                timeout=self._timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise MicrosoftGraphTokenError(
                "Microsoft Graph token request failed"
            ) from error
        if response.status_code != 200:
            raise MicrosoftGraphTokenError(
                f"Microsoft Graph token request failed with HTTP {response.status_code}"
            )
        payload = _response_object(response)
        raw_token = payload.get("access_token")
        if not isinstance(raw_token, str):
            raise MicrosoftGraphTokenError(
                "Microsoft Graph token response is missing access_token"
            )
        token = MicrosoftGraphAccessToken(raw_token)
        _validate_claims(
            token,
            tenant_id=self._credentials.tenant_id,
            client_id=self._credentials.client_id,
        )
        return token


def _response_object(response: httpx.Response) -> JsonObject:
    try:
        value: object = response.json()
    except ValueError as error:
        raise MicrosoftGraphTokenError(
            "Microsoft Graph token response is not JSON"
        ) from error
    if not isinstance(value, dict):
        raise MicrosoftGraphTokenError(
            "Microsoft Graph token response must be an object"
        )
    return cast(JsonObject, cast(dict[str, object], value))


def _validate_claims(
    token: MicrosoftGraphAccessToken,
    *,
    tenant_id: UUID,
    client_id: UUID,
) -> None:
    parts = token.value.split(".")
    if len(parts) != 3:
        raise MicrosoftGraphTokenError("Microsoft Graph access token is malformed")
    encoded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        value: object = json.loads(base64.urlsafe_b64decode(encoded))
    except (ValueError, binascii.Error) as error:
        raise MicrosoftGraphTokenError(
            "Microsoft Graph access token claims are malformed"
        ) from error
    if not isinstance(value, dict):
        raise MicrosoftGraphTokenError(
            "Microsoft Graph access token claims must be an object"
        )
    claims = cast(dict[object, object], value)
    if claims.get("tid") != str(tenant_id):
        raise MicrosoftGraphTokenError("Microsoft Graph token tenant does not match")
    token_client_id = claims.get("appid") or claims.get("azp")
    if token_client_id != str(client_id):
        raise MicrosoftGraphTokenError("Microsoft Graph token client does not match")
    raw_roles = claims.get("roles")
    if not isinstance(raw_roles, list):
        raise MicrosoftGraphTokenError(
            "Microsoft Graph app token has no application roles"
        )
    role_values = cast(list[object], raw_roles)
    if not all(isinstance(role, str) for role in role_values):
        raise MicrosoftGraphTokenError(
            "Microsoft Graph app token has invalid application roles"
        )
    roles = frozenset(cast(list[str], role_values))
    if roles.isdisjoint(_MEMBERSHIP_ROLES):
        supported = " or ".join(sorted(_MEMBERSHIP_ROLES))
        raise MicrosoftGraphTokenError(
            f"Microsoft Graph app token requires {supported}"
        )
