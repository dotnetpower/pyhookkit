"""Microsoft Graph Team membership provisioning tests."""

from uuid import UUID

import httpx
import pytest

from pyhookkit.adapters.outbound.teams.graph_membership import (
    MicrosoftGraphAccessToken,
    TeamsGraphMembershipError,
    TeamsGraphMembershipProvisioner,
)
from pyhookkit.json_types import JsonObject

_TEAM_ID = UUID("11111111-1111-4111-8111-111111111111")
_USER_ID = UUID("22222222-2222-4222-8222-222222222222")
_TOKEN = "synthetic-graph-token"


class StubRequest:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
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
        return self._responses.pop(0)


def _response(status: int, payload: object = None) -> httpx.Response:
    return httpx.Response(status, json={} if payload is None else payload)


def test_existing_member_is_idempotent_and_token_is_redacted() -> None:
    request = StubRequest([_response(200, {"value": [{"id": str(_USER_ID)}]})])
    token = MicrosoftGraphAccessToken(_TOKEN)

    result = TeamsGraphMembershipProvisioner(
        token,
        request=request,
    ).ensure_member(_TEAM_ID, str(_USER_ID))

    assert result.user_id == _USER_ID
    assert result.added is False
    assert len(request.calls) == 1
    assert _TOKEN not in repr(token)


def test_resolves_user_and_adds_non_owner_member_across_pages() -> None:
    next_link = (
        f"https://graph.microsoft.com/v1.0/groups/{_TEAM_ID}/members?$skiptoken=next"
    )
    request = StubRequest(
        [
            _response(200, {"id": str(_USER_ID)}),
            _response(200, {"value": [], "@odata.nextLink": next_link}),
            _response(200, {"value": []}),
            _response(204),
        ]
    )

    result = TeamsGraphMembershipProvisioner(
        MicrosoftGraphAccessToken(_TOKEN),
        request=request,
    ).ensure_member(_TEAM_ID, "svc-teams-notification@example.com")

    assert result.added is True
    assert request.calls[0][0] == "GET"
    assert "svc-teams-notification%40example.com" in request.calls[0][1]
    method, url, payload = request.calls[-1]
    assert method == "POST"
    assert url.endswith(f"/groups/{_TEAM_ID}/members/$ref")
    assert payload is not None
    assert payload["@odata.id"] == (
        f"https://graph.microsoft.com/v1.0/directoryObjects/{_USER_ID}"
    )


def test_conflict_is_success_only_when_member_now_exists() -> None:
    request = StubRequest(
        [
            _response(200, {"value": []}),
            _response(400),
            _response(200, {"value": [{"id": str(_USER_ID)}]}),
        ]
    )

    result = TeamsGraphMembershipProvisioner(
        MicrosoftGraphAccessToken(_TOKEN),
        request=request,
    ).ensure_member(_TEAM_ID, str(_USER_ID))

    assert result.added is False


@pytest.mark.parametrize(
    "responses, message",
    [
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
        (
            [_response(200, {"value": []}), _response(403)],
            "HTTP 403",
        ),
        (
            [_response(200, {"value": "invalid"})],
            "malformed",
        ),
    ],
)
def test_provisioning_rejects_graph_failures(
    responses: list[httpx.Response],
    message: str,
) -> None:
    provisioner = TeamsGraphMembershipProvisioner(
        MicrosoftGraphAccessToken(_TOKEN),
        request=StubRequest(responses),
    )

    with pytest.raises(TeamsGraphMembershipError, match=message):
        provisioner.ensure_member(_TEAM_ID, str(_USER_ID))


def test_user_lookup_rejects_invalid_identifier() -> None:
    provisioner = TeamsGraphMembershipProvisioner(
        MicrosoftGraphAccessToken(_TOKEN),
        request=StubRequest([_response(200, {"id": "not-a-guid"})]),
    )

    with pytest.raises(TeamsGraphMembershipError, match="invalid user ID"):
        provisioner.ensure_member(_TEAM_ID, "svc@example.com")


def test_configuration_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="access token"):
        MicrosoftGraphAccessToken("short")
    with pytest.raises(ValueError, match="timeout"):
        TeamsGraphMembershipProvisioner(
            MicrosoftGraphAccessToken(_TOKEN),
            request=StubRequest([]),
            timeout_seconds=0,
        )
