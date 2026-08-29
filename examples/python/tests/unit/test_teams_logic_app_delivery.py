"""Azure Logic App Teams delivery tests."""

import json
from typing import ClassVar

import httpx
import pytest

import pyhookkit.entrypoints.teams_logic_app_example as entrypoint
from pyhookkit.adapters.outbound.teams.logic_app_destination import (
    TeamsLogicAppDestination,
)
from pyhookkit.adapters.outbound.teams.logic_app_request import (
    TeamsLogicAppRequestError,
    TeamsLogicAppTarget,
    build_teams_logic_app_request,
)
from pyhookkit.adapters.outbound.teams.logic_app_url import TeamsLogicAppUrl
from pyhookkit.adapters.outbound.teams.retry_policy import TeamsRetryPolicy
from pyhookkit.domain.delivery import DeliveryErrorKind, DeliveryResult, DeliveryState
from pyhookkit.json_types import JsonObject

_URL = (
    "https://prod-00.example.logic.azure.com/workflows/example/"
    "triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual"
    "%2Frun&sv=1.0&sig=synthetic"
)


def _envelope() -> JsonObject:
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [{"type": "TextBlock", "text": "Synthetic card"}],
                },
            }
        ],
    }


def test_logic_app_url_is_validated_and_redacted() -> None:
    url = TeamsLogicAppUrl(_URL)

    assert url.value == _URL
    assert _URL not in repr(url)
    with pytest.raises(ValueError, match="invalid Teams Logic App"):
        TeamsLogicAppUrl("https://example.com/triggers/manual/invoke?sig=synthetic")


def test_logic_app_request_extracts_card_and_adds_routing() -> None:
    request = build_teams_logic_app_request(
        _envelope(),
        TeamsLogicAppTarget("team-example", "channel-example"),
        event_id="event-example",
    )

    assert request["teamId"] == "team-example"
    assert request["channelId"] == "channel-example"
    assert request["eventId"] == "event-example"
    card = request["card"]
    assert isinstance(card, dict)
    assert card["type"] == "AdaptiveCard"
    assert "attachments" not in request


@pytest.mark.parametrize(
    "envelope",
    [
        {},
        {"attachments": []},
        {"attachments": [{"contentType": "text/plain"}]},
    ],
)
def test_logic_app_request_rejects_non_card_envelope(envelope: JsonObject) -> None:
    with pytest.raises(TeamsLogicAppRequestError):
        build_teams_logic_app_request(
            envelope,
            TeamsLogicAppTarget("team-example", "channel-example"),
        )


@pytest.mark.parametrize(
    ("team_id", "channel_id"),
    [("", "channel-example"), ("team-example", "")],
)
def test_logic_app_target_rejects_blank_ids(
    team_id: str,
    channel_id: str,
) -> None:
    with pytest.raises(TeamsLogicAppRequestError):
        TeamsLogicAppTarget(team_id, channel_id)


@pytest.mark.parametrize(
    ("status", "state", "kind"),
    [
        (201, DeliveryState.SUCCEEDED, None),
        (400, DeliveryState.FAILED, DeliveryErrorKind.INVALID_PAYLOAD),
        (401, DeliveryState.FAILED, DeliveryErrorKind.AUTHENTICATION),
        (403, DeliveryState.FAILED, DeliveryErrorKind.PERMISSION),
        (429, DeliveryState.FAILED, DeliveryErrorKind.RATE_LIMITED),
        (503, DeliveryState.FAILED, DeliveryErrorKind.TRANSIENT_PROVIDER),
    ],
)
def test_logic_app_destination_classifies_response(
    status: int,
    state: DeliveryState,
    kind: DeliveryErrorKind | None,
) -> None:
    result = TeamsLogicAppDestination(
        TeamsLogicAppUrl(_URL),
        post=lambda *_args, **_kwargs: httpx.Response(status),
        retry_policy=TeamsRetryPolicy(max_attempts=1),
    ).send({"teamId": "team-example"})

    assert result.state is state
    if kind is None:
        assert result.error is None
    else:
        assert result.error is not None
        assert result.error.kind is kind


def test_logic_app_destination_redacts_transport_failure() -> None:
    def fail(*_args: object, **_kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("synthetic transport failure")

    result = TeamsLogicAppDestination(
        TeamsLogicAppUrl(_URL),
        post=fail,
        retry_policy=TeamsRetryPolicy(max_attempts=1),
    ).send({})

    assert result.error is not None
    assert result.error.kind is DeliveryErrorKind.TRANSPORT
    assert result.error.retryable


class StubDestination:
    result: ClassVar[DeliveryResult] = DeliveryResult(
        DeliveryState.SUCCEEDED,
        attempts=1,
    )
    request: ClassVar[JsonObject | None] = None

    def __init__(self, url: TeamsLogicAppUrl) -> None:
        assert url.value == _URL

    def send(self, request: JsonObject) -> DeliveryResult:
        self.__class__.request = request
        return self.result


def test_logic_app_entrypoint_builds_request_and_reports_result(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(entrypoint, "TeamsLogicAppDestination", StubDestination)

    entrypoint.send_teams_logic_app_example(
        _envelope(),
        event_id="event-example",
        environment={
            "TEAMS_LOGIC_APP_URL": _URL,
            "TEAMS_LOGIC_APP_TEAM_ID": "team-example",
            "TEAMS_LOGIC_APP_CHANNEL_ID": "channel-example",
        },
    )

    assert json.loads(capsys.readouterr().out) == {
        "state": "succeeded",
        "attempts": 1,
    }
    assert StubDestination.request is not None
    assert StubDestination.request["eventId"] == "event-example"


@pytest.mark.parametrize(
    "missing_variable",
    (
        "TEAMS_LOGIC_APP_URL",
        "TEAMS_LOGIC_APP_TEAM_ID",
        "TEAMS_LOGIC_APP_CHANNEL_ID",
    ),
)
def test_logic_app_entrypoint_requires_configuration(
    missing_variable: str,
) -> None:
    environment = {
        "TEAMS_LOGIC_APP_URL": _URL,
        "TEAMS_LOGIC_APP_TEAM_ID": "team-example",
        "TEAMS_LOGIC_APP_CHANNEL_ID": "channel-example",
    }
    del environment[missing_variable]

    with pytest.raises(ValueError, match=missing_variable):
        entrypoint.send_teams_logic_app_example(
            _envelope(),
            event_id=None,
            environment=environment,
        )
