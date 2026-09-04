"""Central notification router client composition tests."""

import json
from pathlib import Path

import pytest

import pyhookkit.entrypoints.notification_router_client as entrypoint
from pyhookkit.adapters.outbound.router_client import RouterSubmissionResult


class StubClient:
    def __init__(
        self,
        url: object,
        token: object,
        producer: str,
    ) -> None:
        assert "127.0.0.1" not in repr(url)
        assert "synthetic-router-token" not in repr(token)
        assert producer == "gitlab"

    def submit(self, payload: object) -> RouterSubmissionResult:
        assert isinstance(payload, dict)
        assert payload["eventId"] == "scenario-deployment-result-001"
        return RouterSubmissionResult(
            "11111111-1111-4111-8111-111111111111",
            False,
            "queued",
        )


def test_client_entrypoint_loads_and_submits_canonical_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository_root = Path(__file__).resolve().parents[4]
    input_path = (
        repository_root
        / "contracts"
        / "test-vectors"
        / "scenarios"
        / "deployment-result"
        / "notification.json"
    )
    monkeypatch.setattr(entrypoint, "NotificationRouterClient", StubClient)

    entrypoint.run_notification_router_client(
        arguments=["--input", str(input_path), "--producer", "gitlab"],
        environment={
            "NOTIFICATION_ROUTER_URL": "http://127.0.0.1:8080",
            "NOTIFICATION_ROUTER_TOKEN": "synthetic-router-token",
        },
    )

    assert json.loads(capsys.readouterr().out)["state"] == "queued"


def test_client_entrypoint_requires_environment(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="NOTIFICATION_ROUTER_URL"):
        entrypoint.run_notification_router_client(
            arguments=[
                "--input",
                str(tmp_path / "missing.json"),
                "--producer",
                "gitlab",
            ],
            environment={},
        )
