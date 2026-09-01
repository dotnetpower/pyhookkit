"""Automation CLI tests for reusable scenarios."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

import pyhookkit.entrypoints.scenario_cli as entrypoint
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.ports.message_renderer import MessageRenderer

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_SCENARIO_VECTORS = _REPOSITORY_ROOT / "contracts" / "test-vectors" / "scenarios"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _deployment_args(provider: str, *, send: bool = False) -> list[str]:
    arguments = [
        "deployment-result",
        provider,
        "--event-id",
        "scenario-deployment-result-001",
        "--correlation-id",
        "deploy-run-1042",
        "--service",
        "example-api",
        "--deployment-environment",
        "staging",
        "--revision",
        "9f3a2c1",
        "--duration",
        "2m 18s",
        "--completed-at",
        "2026-08-28T03:15:00Z",
        "--deployment-url",
        "https://deployments.example.com/runs/run-1042",
    ]
    if send:
        arguments.append("--send")
    return arguments


def _approval_teams_args() -> list[str]:
    return [
        "approval-request",
        "teams",
        "--event-id",
        "scenario-approval-request-001",
        "--correlation-id",
        "approval-apr-307",
        "--request-id",
        "APR-307",
        "--subject",
        "example-api 2026.08.28",
        "--requester",
        "example-requester",
        "--requested-at",
        "2026-08-28T05:10:00Z",
        "--deadline-at",
        "2026-08-28T07:00:00Z",
        "--approver-alias",
        "example-approver",
        "--review-url",
        "https://approvals.example.com/requests/apr-307",
        "--teams-approver-id",
        "example-approver@pyhookkit.example",
        "--teams-approver-name",
        "Example Approver",
    ]


def _incident_slack_args() -> list[str]:
    return [
        "incident-alert-acknowledgment",
        "slack",
        "--event-id",
        "scenario-incident-alert-001",
        "--correlation-id",
        "incident-inc-204",
        "--incident-id",
        "INC-204",
        "--incident-service",
        "example-checkout",
        "--started-at",
        "2026-08-28T04:20:00Z",
        "--status",
        "unacknowledged",
        "--responder-alias",
        "example-responders",
        "--acknowledgment-url",
        "https://incidents.example.com/incidents/inc-204/acknowledge",
        "--runbook-url",
        "https://runbooks.example.com/services/example-checkout/latency",
    ]


def _input_path(vector_name: str) -> Path:
    return _SCENARIO_VECTORS / vector_name / "notification.json"


def test_cli_renders_deployment_result_for_slack(
    capsys: pytest.CaptureFixture[str],
) -> None:
    entrypoint.run_notification_automation(arguments=_deployment_args("slack"))

    assert json.loads(capsys.readouterr().out) == _load_json(
        _SCENARIO_VECTORS / "deployment-result" / "slack.expected.json"
    )


def test_cli_renders_approval_request_for_teams(
    capsys: pytest.CaptureFixture[str],
) -> None:
    entrypoint.run_notification_automation(arguments=_approval_teams_args())

    payload = json.loads(capsys.readouterr().out)
    serialized = json.dumps(payload)

    assert "assets.pyhookkit.example" not in serialized
    assert '"backgroundImage"' not in serialized
    assert "Example Approver" in serialized
    assert "https://approvals.example.com/requests/apr-307" in serialized


def test_cli_accepts_canonical_input_file_with_provider_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    entrypoint.run_notification_automation(
        arguments=[
            "--input",
            str(_input_path("deployment-result")),
            "--provider",
            "slack",
        ]
    )

    assert json.loads(capsys.readouterr().out) == _load_json(
        _SCENARIO_VECTORS / "deployment-result" / "slack.expected.json"
    )


def test_cli_renders_teams_input_without_synthetic_hero_by_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    entrypoint.run_notification_automation(
        arguments=[
            "approval-request",
            "teams",
            "--input",
            str(_input_path("approval-request")),
            "--teams-user-identity",
            "example-approver=example-approver@pyhookkit.example",
            "--teams-user-display-name",
            "example-approver=Example Approver",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    serialized = json.dumps(payload)

    assert "assets.pyhookkit.example" not in serialized
    assert '"backgroundImage"' not in serialized
    assert "Example Approver" in serialized


def test_cli_uses_explicit_public_hero_image_when_provided(
    capsys: pytest.CaptureFixture[str],
) -> None:
    entrypoint.run_notification_automation(
        arguments=[
            *_approval_teams_args(),
            "--hero-image-url",
            "https://cdn.example.com/assets/approval.png",
        ]
    )

    serialized = json.dumps(json.loads(capsys.readouterr().out))

    assert "https://cdn.example.com/assets/approval.png" in serialized
    assert "assets.pyhookkit.example" not in serialized


def test_cli_requires_explicit_slack_group_identity(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        entrypoint.run_notification_automation(arguments=_incident_slack_args())

    assert "--slack-responder-group-id is required" in capsys.readouterr().err


def test_cli_requires_explicit_input_identity_mappings() -> None:
    with pytest.raises(
        ValueError,
        match="--slack-user-identity alias=USER_ID is required",
    ):
        entrypoint.run_notification_automation(
            arguments=[
                "approval-request",
                "slack",
                "--input",
                str(_input_path("approval-request")),
            ]
        )


def test_cli_sends_only_with_send_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded_arguments: list[Sequence[str] | None] = []

    def run_slack(
        _notification: object,
        _renderer: object,
        *,
        arguments: Sequence[str] | None = None,
        environment: object = None,
    ) -> None:
        del environment
        recorded_arguments.append(arguments)

    monkeypatch.setattr(entrypoint, "run_slack_webhook_example", run_slack)

    entrypoint.run_notification_automation(arguments=_deployment_args("slack"))
    entrypoint.run_notification_automation(
        arguments=_deployment_args("slack", send=True)
    )

    assert recorded_arguments == [[], ["--send"]]


def test_module_accepts_gitlab_style_input_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded_arguments: list[Sequence[str] | None] = []
    rendered_payloads: list[object] = []

    def run_teams(
        _notification: CanonicalNotification,
        _renderer: MessageRenderer,
        *,
        arguments: Sequence[str] | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        del environment
        recorded_arguments.append(arguments)
        rendered_payloads.append(_renderer.render(_notification))

    monkeypatch.setattr(entrypoint, "run_teams_workflow_example", run_teams)

    entrypoint.run_notification_automation(
        arguments=[
            "--input",
            str(_input_path("deployment-result")),
            "--provider",
            "teams",
            "--send",
        ]
    )

    assert recorded_arguments == [["--send"]]
    assert "assets.pyhookkit.example" not in json.dumps(rendered_payloads[0])
