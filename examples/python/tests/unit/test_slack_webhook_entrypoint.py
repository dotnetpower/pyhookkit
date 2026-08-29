"""Slack webhook example composition tests."""

import json
from typing import ClassVar

import pytest

import pyhookkit.entrypoints.slack_webhook_example as entrypoint
from pyhookkit.adapters.outbound.slack.route_resolver import (
    SlackRouteNotConfiguredError,
)
from pyhookkit.adapters.outbound.slack.text_renderer import SlackTextRenderer
from pyhookkit.adapters.outbound.slack.webhook_url import SlackWebhookUrl
from pyhookkit.domain.delivery import (
    DeliveryError,
    DeliveryErrorKind,
    DeliveryResult,
    DeliveryState,
)
from pyhookkit.domain.notification import CanonicalNotification, Severity
from pyhookkit.json_types import JsonObject

_WEBHOOK_URL = "https://hooks.slack.com/services/example"


class StubDestination:
    """Capture entrypoint delivery without using the network."""

    result: ClassVar[DeliveryResult] = DeliveryResult(
        DeliveryState.SUCCEEDED,
        attempts=1,
    )
    expected_payload: ClassVar[JsonObject] = {"text": "Synthetic example"}

    def __init__(self, webhook_url: SlackWebhookUrl) -> None:
        assert webhook_url.value == _WEBHOOK_URL

    def send(self, payload: JsonObject) -> DeliveryResult:
        assert payload == self.expected_payload
        return self.result


def _notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-entrypoint-001",
        route="platform-alerts",
        body="Synthetic example",
        severity=Severity.INFO,
    )


def test_entrypoint_renders_without_environment(
    capsys: pytest.CaptureFixture[str],
) -> None:
    entrypoint.run_slack_webhook_example(
        _notification(),
        SlackTextRenderer(),
        arguments=[],
        environment={},
    )

    assert json.loads(capsys.readouterr().out) == {"text": "Synthetic example"}


def test_entrypoint_checks_route_without_printing_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    entrypoint.run_slack_webhook_example(
        _notification(),
        SlackTextRenderer(),
        arguments=["--check-route"],
        environment={"SLACK_WEBHOOK_URL": _WEBHOOK_URL},
    )

    assert capsys.readouterr().out == "Slack route configured\n"


def test_entrypoint_rejects_missing_route() -> None:
    with pytest.raises(SlackRouteNotConfiguredError):
        entrypoint.run_slack_webhook_example(
            _notification(),
            SlackTextRenderer(),
            arguments=["--check-route"],
            environment={},
        )


def test_entrypoint_sends_and_serializes_result(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    StubDestination.result = DeliveryResult(
        DeliveryState.SUCCEEDED,
        attempts=1,
    )
    StubDestination.expected_payload = {"text": "Synthetic example"}
    monkeypatch.setattr(entrypoint, "SlackWebhookDestination", StubDestination)

    entrypoint.run_slack_webhook_example(
        _notification(),
        SlackTextRenderer(),
        arguments=["--send"],
        environment={"SLACK_WEBHOOK_URL": _WEBHOOK_URL},
    )

    assert json.loads(capsys.readouterr().out) == {
        "state": "succeeded",
        "attempts": 1,
    }


def test_entrypoint_resolves_public_asset_before_sending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AssetRenderer:
        def render(self, notification: CanonicalNotification) -> JsonObject:
            assert notification.body == "Synthetic example"
            return {
                "image_url": "https://assets.pyhookkit.example/sample.png",
            }

    StubDestination.result = DeliveryResult(
        DeliveryState.SUCCEEDED,
        attempts=1,
    )
    StubDestination.expected_payload = {
        "image_url": "https://cdn.example.com/assets/sample.png",
    }
    monkeypatch.setattr(entrypoint, "SlackWebhookDestination", StubDestination)

    entrypoint.run_slack_webhook_example(
        _notification(),
        AssetRenderer(),
        arguments=["--send"],
        environment={
            "SLACK_WEBHOOK_URL": _WEBHOOK_URL,
            "EXAMPLE_ASSET_BASE_URL": "https://cdn.example.com/assets",
        },
    )


def test_entrypoint_exits_nonzero_on_delivery_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    StubDestination.result = DeliveryResult(
        DeliveryState.FAILED,
        attempts=3,
        error=DeliveryError(
            DeliveryErrorKind.TRANSIENT_PROVIDER,
            retryable=True,
            status_code=503,
        ),
    )
    StubDestination.expected_payload = {"text": "Synthetic example"}
    monkeypatch.setattr(entrypoint, "SlackWebhookDestination", StubDestination)

    with pytest.raises(SystemExit):
        entrypoint.run_slack_webhook_example(
            _notification(),
            SlackTextRenderer(),
            arguments=["--send"],
            environment={"SLACK_WEBHOOK_URL": _WEBHOOK_URL},
        )

    assert json.loads(capsys.readouterr().out)["state"] == "failed"
