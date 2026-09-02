"""Teams channel-link routing tests."""

from uuid import UUID

import pytest

from pyhookkit.adapters.outbound.teams.channel_link import (
    TeamsChannelLink,
    TeamsChannelLinkError,
)
from pyhookkit.adapters.outbound.teams.workflow_request import (
    TeamsWorkflowRequestError,
    build_teams_workflow_request,
)
from pyhookkit.json_types import JsonObject

_LINK = (
    "https://teams.microsoft.com/l/channel/"
    "19%3Aexample-channel%40thread.tacv2/General"
    "?groupId=11111111-1111-4111-8111-111111111111"
    "&tenantId=22222222-2222-4222-8222-222222222222"
)


def _envelope() -> JsonObject:
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {"type": "AdaptiveCard"},
            }
        ],
    }


def test_channel_link_extracts_provider_identifiers() -> None:
    link = TeamsChannelLink(_LINK)

    assert link.team_id == UUID("11111111-1111-4111-8111-111111111111")
    assert link.channel_id == "19:example-channel@thread.tacv2"
    assert link.tenant_id == UUID("22222222-2222-4222-8222-222222222222")
    assert _LINK not in repr(link)


@pytest.mark.parametrize(
    "link",
    [
        "http://teams.microsoft.com/l/channel/19%3Ax%40thread.tacv2/General"
        "?groupId=11111111-1111-4111-8111-111111111111"
        "&tenantId=22222222-2222-4222-8222-222222222222",
        "https://example.com/l/channel/19%3Ax%40thread.tacv2/General"
        "?groupId=11111111-1111-4111-8111-111111111111"
        "&tenantId=22222222-2222-4222-8222-222222222222",
        "https://teams.microsoft.com/l/channel/not-a-channel/General"
        "?groupId=11111111-1111-4111-8111-111111111111"
        "&tenantId=22222222-2222-4222-8222-222222222222",
        "https://teams.microsoft.com/l/channel/19%3Ax%40thread.tacv2/General"
        "?groupId=not-a-guid"
        "&tenantId=22222222-2222-4222-8222-222222222222",
        "https://teams.microsoft.com/l/channel/19%3Ax%40thread.tacv2/General"
        "?groupId&tenantId=22222222-2222-4222-8222-222222222222",
    ],
)
def test_channel_link_rejects_invalid_destinations(link: str) -> None:
    with pytest.raises(TeamsChannelLinkError):
        TeamsChannelLink(link)


def test_workflow_request_adds_link_and_preserves_message() -> None:
    envelope = _envelope()

    request = build_teams_workflow_request(envelope, TeamsChannelLink(_LINK))

    assert request["channelLink"] == _LINK
    assert request["teamId"] == "11111111-1111-4111-8111-111111111111"
    assert request["channelId"] == "19:example-channel@thread.tacv2"
    assert request["attachments"] is envelope["attachments"]
    assert "channelLink" not in envelope


@pytest.mark.parametrize(
    "envelope",
    [
        {},
        {"type": "message", "attachments": []},
        {"type": "message", "attachments": [{"contentType": "text/plain"}]},
    ],
)
def test_workflow_request_rejects_incomplete_message(envelope: JsonObject) -> None:
    with pytest.raises(TeamsWorkflowRequestError):
        build_teams_workflow_request(envelope, TeamsChannelLink(_LINK))
