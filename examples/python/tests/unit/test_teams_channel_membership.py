"""Microsoft Graph private channel membership tests."""

from uuid import UUID

import httpx
import pytest

from pyhookkit.adapters.outbound.teams.channel_membership import (
    TeamsGraphChannelMembershipProvisioner,
)
from pyhookkit.adapters.outbound.teams.graph_membership import (
    MicrosoftGraphAccessToken,
    TeamsGraphMembershipError,
)
from pyhookkit.json_types import JsonObject

_TEAM_ID = UUID("11111111-1111-4111-8111-111111111111")
_USER_ID = UUID("22222222-2222-4222-8222-222222222222")
_CHANNEL_ID = "19:private-channel@thread.tacv2"
_TOKEN = "synthetic-graph-token"


class StubRequest:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, JsonObject | None]] = []

    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: JsonObject | None,
        timeout: float,
    ) -> httpx.Response:
        assert headers["Authorization"] == f"Bearer {_TOKEN}"
        assert timeout == 15.0
        self.calls.append((method, url, json))
        return self.responses.pop(0)


def _response(status: int, payload: object = None) -> httpx.Response:
    return httpx.Response(status, json={} if payload is None else payload)


def test_existing_private_channel_member_is_idempotent() -> None:
    request = StubRequest([_response(200, {"value": [{"userId": str(_USER_ID)}]})])

    result = TeamsGraphChannelMembershipProvisioner(
        MicrosoftGraphAccessToken(_TOKEN),
        request=request,
    ).ensure_member(_TEAM_ID, _CHANNEL_ID, _USER_ID)

    assert result.added is False
    assert len(request.calls) == 1


def test_adds_private_channel_member() -> None:
    request = StubRequest([_response(200, {"value": []}), _response(201)])

    result = TeamsGraphChannelMembershipProvisioner(
        MicrosoftGraphAccessToken(_TOKEN),
        request=request,
    ).ensure_member(_TEAM_ID, _CHANNEL_ID, _USER_ID)

    assert result.added is True
    method, url, payload = request.calls[-1]
    assert method == "POST"
    assert "/channels/19%3Aprivate-channel%40thread.tacv2/members" in url
    assert payload == {
        "@odata.type": "#microsoft.graph.aadUserConversationMember",
        "roles": [],
        "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{_USER_ID}')",
    }


def test_conflict_is_success_only_when_channel_member_exists() -> None:
    request = StubRequest(
        [
            _response(200, {"value": []}),
            _response(409),
            _response(200, {"value": [{"userId": str(_USER_ID)}]}),
        ]
    )

    result = TeamsGraphChannelMembershipProvisioner(
        MicrosoftGraphAccessToken(_TOKEN),
        request=request,
    ).ensure_member(_TEAM_ID, _CHANNEL_ID, _USER_ID)

    assert result.added is False


@pytest.mark.parametrize(
    ("responses", "message"),
    [
        ([_response(200, {"value": []}), _response(403)], "HTTP 403"),
        ([_response(200, {"value": "invalid"})], "malformed"),
        (
            [
                _response(
                    200,
                    {
                        "value": [],
                        "@odata.nextLink": "https://example.test/token-capture",
                    },
                )
            ],
            "unexpected origin",
        ),
    ],
)
def test_private_channel_membership_rejects_graph_failures(
    responses: list[httpx.Response],
    message: str,
) -> None:
    provisioner = TeamsGraphChannelMembershipProvisioner(
        MicrosoftGraphAccessToken(_TOKEN),
        request=StubRequest(responses),
    )

    with pytest.raises(TeamsGraphMembershipError, match=message):
        provisioner.ensure_member(_TEAM_ID, _CHANNEL_ID, _USER_ID)


def test_private_channel_membership_rejects_invalid_timeout() -> None:
    with pytest.raises(ValueError, match="timeout"):
        TeamsGraphChannelMembershipProvisioner(
            MicrosoftGraphAccessToken(_TOKEN),
            timeout_seconds=0,
        )
