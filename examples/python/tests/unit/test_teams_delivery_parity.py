"""Workflow and Logic App example delivery parity tests."""

import json
import runpy
import sys
from pathlib import Path
from typing import ClassVar, cast

import pytest

import pyhookkit.entrypoints.teams_card_example as card_entrypoint
import pyhookkit.entrypoints.teams_logic_app_example as logic_app_entrypoint
import pyhookkit.entrypoints.teams_workflow_example as workflow_entrypoint
from pyhookkit.adapters.outbound.teams.identity import TeamsIdentityNotFoundError
from pyhookkit.adapters.outbound.teams.logic_app_url import TeamsLogicAppUrl
from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.domain.delivery import DeliveryResult, DeliveryState
from pyhookkit.json_types import JsonObject, JsonValue

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_PYTHON_ROOT = _REPOSITORY_ROOT / "examples" / "python"
_EXAMPLES = (
    "fundamentals/01_hello_world/teams.py",
    "fundamentals/02_basic_notification/teams.py",
    "fundamentals/03_rich_card/teams.py",
    "fundamentals/04_mention/teams.py",
    "fundamentals/05_link_and_action/teams.py",
    "fundamentals/06_image/teams.py",
    "fundamentals/07_routing/teams.py",
    "fundamentals/08_thread_or_reply/teams.py",
    "fundamentals/09_update_and_delete/teams.py",
    "fundamentals/10_error_and_retry/teams.py",
    "scenarios/deployment_result/teams.py",
    "scenarios/incident_alert_acknowledgment/teams.py",
    "scenarios/approval_request/teams.py",
    "scenarios/maintenance_notice/teams.py",
    "teams_adaptive_cards/00_visual_hierarchy/teams.py",
    "teams_adaptive_cards/01_metrics_dashboard/teams.py",
    "teams_adaptive_cards/02_hero_image/teams.py",
    "teams_adaptive_cards/03_progressive_disclosure/teams.py",
    "teams_adaptive_cards/04_user_mention/teams.py",
    "teams_adaptive_cards/05_progress_timeline/teams.py",
    "teams_adaptive_cards/06_image_gallery/teams.py",
)
_SUCCESS = DeliveryResult(DeliveryState.SUCCEEDED, attempts=1)


class StubWorkflowDestination:
    payloads: ClassVar[list[JsonObject]] = []

    def __init__(self, url: TeamsWorkflowUrl) -> None:
        self._url = url

    def send(self, payload: JsonObject) -> DeliveryResult:
        self.__class__.payloads.append(payload)
        return _SUCCESS


class StubLogicAppDestination:
    requests: ClassVar[list[JsonObject]] = []

    def __init__(self, url: TeamsLogicAppUrl) -> None:
        self._url = url

    def send(self, request: JsonObject) -> DeliveryResult:
        self.__class__.requests.append(request)
        return _SUCCESS


def _card(envelope: JsonObject) -> JsonObject:
    attachments = envelope["attachments"]
    assert isinstance(attachments, list)
    attachment_value: JsonValue = attachments[0]
    assert isinstance(attachment_value, dict)
    attachment = cast(JsonObject, attachment_value)
    card = attachment["content"]
    assert isinstance(card, dict)
    return cast(JsonObject, card)


def _run_example(
    path: Path,
    option: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", [str(path), option])
    runpy.run_path(str(path), run_name="__main__")


@pytest.mark.parametrize("relative_path", _EXAMPLES)
def test_example_preserves_card_between_delivery_adapters(
    relative_path: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _PYTHON_ROOT / relative_path
    monkeypatch.setattr(sys, "path", [str(path.parent), *sys.path])
    monkeypatch.delitem(sys.modules, "example_notification", raising=False)
    monkeypatch.setenv(
        "TEAMS_WORKFLOW_URL",
        "https://default-example.environment.api.powerplatform.com/"
        "workflows/example/triggers/manual/paths/invoke?sig=synthetic",
    )
    monkeypatch.setenv(
        "TEAMS_WORKFLOW_CHANNEL_LINK",
        "https://teams.microsoft.com/l/channel/"
        "19%3Aexample-channel%40thread.tacv2/General"
        "?groupId=11111111-1111-4111-8111-111111111111"
        "&tenantId=22222222-2222-4222-8222-222222222222",
    )
    monkeypatch.setenv(
        "TEAMS_LOGIC_APP_URL",
        "https://example.logic.azure.com/workflows/example/"
        "triggers/manual/paths/invoke?sig=synthetic",
    )
    monkeypatch.setenv("TEAMS_LOGIC_APP_TEAM_ID", "team-example")
    monkeypatch.setenv("TEAMS_LOGIC_APP_CHANNEL_ID", "channel-example")
    monkeypatch.setenv(
        "EXAMPLE_ASSET_BASE_URL",
        "https://cdn.pyhookkit.example/assets",
    )
    monkeypatch.setenv(
        "TEAMS_ASSET_BASE_URL",
        "https://legacy.pyhookkit.example/assets",
    )
    monkeypatch.setenv("TEAMS_TEST_USER_ID", "example-owner@pyhookkit.example")
    monkeypatch.setenv("TEAMS_TEST_USER_NAME", "Example Owner")
    monkeypatch.setattr(
        workflow_entrypoint,
        "TeamsWorkflowDestination",
        StubWorkflowDestination,
    )
    monkeypatch.setattr(
        card_entrypoint,
        "TeamsWorkflowDestination",
        StubWorkflowDestination,
    )
    monkeypatch.setattr(
        logic_app_entrypoint,
        "TeamsLogicAppDestination",
        StubLogicAppDestination,
    )
    StubWorkflowDestination.payloads = []
    StubLogicAppDestination.requests = []

    _run_example(path, "--send", monkeypatch)
    workflow_result = json.loads(capsys.readouterr().out)
    _run_example(path, "--send-logic-app", monkeypatch)
    logic_app_result = json.loads(capsys.readouterr().out)

    assert (
        workflow_result
        == logic_app_result
        == {
            "state": "succeeded",
            "attempts": 1,
        }
    )
    assert len(StubWorkflowDestination.payloads) == 1
    assert len(StubLogicAppDestination.requests) == 1
    workflow_payload = StubWorkflowDestination.payloads[0]
    logic_app_request = StubLogicAppDestination.requests[0]
    channel_link = workflow_payload["channelLink"]
    assert isinstance(channel_link, str)
    assert channel_link.startswith("https://teams.microsoft.com/")
    assert logic_app_request["teamId"] == "team-example"
    assert logic_app_request["channelId"] == "channel-example"
    assert logic_app_request["card"] == _card(workflow_payload)
    serialized_request = json.dumps(logic_app_request)
    assert "assets.pyhookkit.example" not in serialized_request
    assert "legacy.pyhookkit.example" not in serialized_request


def test_mention_example_requires_runtime_identity_when_sending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _PYTHON_ROOT / "fundamentals" / "04_mention" / "teams.py"
    monkeypatch.setattr(sys, "path", [str(path.parent), *sys.path])
    monkeypatch.setattr(sys, "argv", [str(path), "--send"])
    monkeypatch.delitem(sys.modules, "example_notification", raising=False)
    monkeypatch.delenv("TEAMS_TEST_USER_ID", raising=False)
    monkeypatch.delenv("TEAMS_TEST_USER_NAME", raising=False)

    with pytest.raises(TeamsIdentityNotFoundError, match="TEAMS_TEST_USER_NAME"):
        runpy.run_path(str(path), run_name="__main__")
