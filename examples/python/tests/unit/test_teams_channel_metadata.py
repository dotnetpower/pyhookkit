"""Microsoft Graph Teams channel metadata tests."""

from uuid import UUID

import httpx
import pytest

from pyhookkit.adapters.outbound.teams.channel_metadata import (
    TeamsChannelMembershipType,
    TeamsGraphChannelInspector,
)
from pyhookkit.adapters.outbound.teams.graph_membership import (
    MicrosoftGraphAccessToken,
    TeamsGraphMembershipError,
)
from pyhookkit.json_types import JsonObject

_TEAM_ID = UUID("11111111-1111-4111-8111-111111111111")
_CHANNEL_ID = "19:example-channel@thread.tacv2"
_TOKEN = MicrosoftGraphAccessToken("synthetic-graph-token")


class StubRequest:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.url = ""

    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: JsonObject | None,
        timeout: float,
    ) -> httpx.Response:
        assert method == "GET"
        assert headers["Authorization"] == "Bearer synthetic-graph-token"
        assert json is None
        assert timeout == 15.0
        self.url = url
        return self.response


@pytest.mark.parametrize(
    "membership_type",
    [
        TeamsChannelMembershipType.STANDARD,
        TeamsChannelMembershipType.PRIVATE,
        TeamsChannelMembershipType.SHARED,
    ],
)
def test_inspector_reads_channel_membership_type(
    membership_type: TeamsChannelMembershipType,
) -> None:
    request = StubRequest(
        httpx.Response(200, json={"membershipType": membership_type.value})
    )

    result = TeamsGraphChannelInspector(_TOKEN, request=request).membership_type(
        _TEAM_ID,
        _CHANNEL_ID,
    )

    assert result is membership_type
    assert "/channels/19%3Aexample-channel%40thread.tacv2" in request.url
    assert request.url.endswith("?$select=membershipType")


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(403), "HTTP 403"),
        (httpx.Response(200, json=[]), "must be an object"),
        (httpx.Response(200, json={}), "malformed"),
        (httpx.Response(200, json={"membershipType": "unknown"}), "unsupported"),
    ],
)
def test_inspector_rejects_graph_failures(
    response: httpx.Response,
    message: str,
) -> None:
    inspector = TeamsGraphChannelInspector(_TOKEN, request=StubRequest(response))

    with pytest.raises(TeamsGraphMembershipError, match=message):
        inspector.membership_type(_TEAM_ID, _CHANNEL_ID)


def test_inspector_rejects_invalid_timeout() -> None:
    with pytest.raises(ValueError, match="timeout"):
        TeamsGraphChannelInspector(_TOKEN, timeout_seconds=0)
