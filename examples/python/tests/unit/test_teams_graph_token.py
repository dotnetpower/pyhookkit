"""Microsoft Graph client-credentials token tests."""

import base64
import json
from collections.abc import Callable
from uuid import UUID

import httpx
import pytest

from pyhookkit.adapters.outbound.teams.graph_token import (
    MicrosoftGraphClientCredentialsTokenProvider,
    MicrosoftGraphTokenError,
    TeamsNotifyAppCredentials,
)

_TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")
_CLIENT_ID = UUID("22222222-2222-4222-8222-222222222222")
_SECRET = "synthetic-client-secret"


def _token(
    *,
    tenant_id: UUID = _TENANT_ID,
    client_id: UUID = _CLIENT_ID,
    roles: list[str] | None = None,
) -> str:
    header = _encoded({"alg": "none", "typ": "JWT"})
    payload = _encoded(
        {
            "tid": str(tenant_id),
            "appid": str(client_id),
            "roles": roles or ["GroupMember.ReadWrite.All"],
        }
    )
    return f"{header}.{payload}.signature"


def _encoded(value: object) -> str:
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")


def _credentials() -> TeamsNotifyAppCredentials:
    return TeamsNotifyAppCredentials(_TENANT_ID, _CLIENT_ID, _SECRET)


class FixedTokenResponse:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    def __call__(
        self,
        url: str,
        *,
        data: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        del url, data, timeout
        return self._response


def test_provider_acquires_valid_app_token_and_redacts_secret() -> None:
    captured: dict[str, object] = {}

    def post(
        url: str,
        *,
        data: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        captured.update(url=url, data=data, timeout=timeout)
        return httpx.Response(200, json={"access_token": _token()})

    credentials = _credentials()
    token = MicrosoftGraphClientCredentialsTokenProvider(
        credentials,
        post=post,
    ).token()

    assert token.value == _token()
    captured_url = captured["url"]
    assert isinstance(captured_url, str)
    assert str(_TENANT_ID) in captured_url
    assert captured["data"] == {
        "client_id": str(_CLIENT_ID),
        "client_secret": _SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    assert _SECRET not in repr(credentials)


@pytest.mark.parametrize(
    "response, message",
    [
        (httpx.Response(401), "HTTP 401"),
        (httpx.Response(200, json={}), "access_token"),
        (httpx.Response(200, json=[]), "must be an object"),
        (
            httpx.Response(
                200,
                json={
                    "access_token": _token(
                        tenant_id=UUID("33333333-3333-4333-8333-333333333333")
                    )
                },
            ),
            "tenant does not match",
        ),
        (
            httpx.Response(
                200,
                json={
                    "access_token": _token(
                        client_id=UUID("33333333-3333-4333-8333-333333333333")
                    )
                },
            ),
            "client does not match",
        ),
        (
            httpx.Response(
                200,
                json={"access_token": _token(roles=["User.Read.All"])},
            ),
            "requires Group",
        ),
    ],
)
def test_provider_rejects_invalid_tokens(
    response: httpx.Response,
    message: str,
) -> None:
    provider = MicrosoftGraphClientCredentialsTokenProvider(
        _credentials(),
        post=FixedTokenResponse(response),
    )

    with pytest.raises(MicrosoftGraphTokenError, match=message):
        provider.token()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: TeamsNotifyAppCredentials(_TENANT_ID, _CLIENT_ID, "short"),
        lambda: MicrosoftGraphClientCredentialsTokenProvider(
            _credentials(),
            timeout_seconds=0,
        ),
    ],
)
def test_token_configuration_rejects_invalid_values(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ValueError):
        factory()
