"""Microsoft Teams Workflow delivery and entrypoint tests."""

import json
from typing import ClassVar

import httpx
import pytest

import pyhookkit.entrypoints.teams_workflow_example as entrypoint
from pyhookkit.adapters.outbound.teams.text_renderer import TeamsTextRenderer
from pyhookkit.adapters.outbound.teams.workflow_destination import (
    TeamsWorkflowDestination,
)
from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.domain.delivery import DeliveryResult, DeliveryState
from pyhookkit.domain.notification import CanonicalNotification, Severity
from pyhookkit.json_types import JsonObject

_URL = (
    "https://default-example.environment.api.powerplatform.com/"
    "powerautomate/automations/direct/workflows/example/triggers/manual/paths/"
    "invoke?api-version=1&sig=synthetic"
)


def _notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-teams-entrypoint-001",
        route="hello-world",
        body="Hello, world!",
        severity=Severity.INFO,
    )


def test_workflow_url_is_validated_and_redacted() -> None:
    url = TeamsWorkflowUrl(_URL)

    assert url.value == _URL
    assert _URL not in repr(url)
    with pytest.raises(ValueError, match="invalid Teams"):
        TeamsWorkflowUrl("https://example.com/workflows/test?sig=synthetic")


@pytest.mark.parametrize(
    ("status", "state"),
    [(202, DeliveryState.SUCCEEDED), (400, DeliveryState.FAILED)],
)
def test_destination_classifies_response(
    status: int,
    state: DeliveryState,
) -> None:
    result = TeamsWorkflowDestination(
        TeamsWorkflowUrl(_URL),
        post=lambda *_args, **_kwargs: httpx.Response(status),
    ).send({"type": "message"})

    assert result.state is state


class StubDestination:
    result: ClassVar[DeliveryResult] = DeliveryResult(
        DeliveryState.SUCCEEDED,
        attempts=1,
    )

    def __init__(self, url: TeamsWorkflowUrl) -> None:
        assert url.value == _URL

    def send(self, payload: JsonObject) -> DeliveryResult:
        assert payload["type"] == "message"
        return self.result


def test_entrypoint_renders_and_sends(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    entrypoint.run_teams_workflow_example(
        _notification(),
        TeamsTextRenderer(),
        arguments=[],
        environment={},
    )
    assert json.loads(capsys.readouterr().out)["type"] == "message"

    monkeypatch.setattr(entrypoint, "TeamsWorkflowDestination", StubDestination)
    entrypoint.run_teams_workflow_example(
        _notification(),
        TeamsTextRenderer(),
        arguments=["--send"],
        environment={"TEAMS_WORKFLOW_URL": _URL},
    )
    assert json.loads(capsys.readouterr().out)["state"] == "succeeded"


def test_entrypoint_routes_logic_app_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def send_logic_app(
        payload: JsonObject,
        *,
        event_id: str | None,
        environment: dict[str, str],
    ) -> None:
        captured["payload"] = payload
        captured["event_id"] = event_id
        captured["environment"] = environment

    monkeypatch.setattr(entrypoint, "send_teams_logic_app_example", send_logic_app)
    environment = {"TEAMS_LOGIC_APP_URL": "synthetic"}

    entrypoint.run_teams_workflow_example(
        _notification(),
        TeamsTextRenderer(),
        arguments=["--send-logic-app"],
        environment=environment,
    )

    assert captured["event_id"] == "example-teams-entrypoint-001"
    assert captured["environment"] is environment
