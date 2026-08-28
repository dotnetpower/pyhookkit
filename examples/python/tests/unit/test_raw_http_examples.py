"""Dependency-free raw HTTP example tests."""

import json
import runpy
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, cast

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_PYTHON_ROOT = _REPOSITORY_ROOT / "examples" / "python"
_EXAMPLE_DIRECTORY = _PYTHON_ROOT / "fundamentals" / "00_http_request"
_VECTOR_DIRECTORY = (
    _REPOSITORY_ROOT / "contracts" / "test-vectors" / "fundamentals" / "hello-world"
)


class Send(Protocol):
    def __call__(self, destination_url: str) -> int: ...


class StubResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "StubResponse":
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> None:
        return None


def _load_script(
    provider: str,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    monkeypatch.setattr(sys, "path", [str(_EXAMPLE_DIRECTORY), *sys.path])
    return runpy.run_path(str(_EXAMPLE_DIRECTORY / f"{provider}.py"))


@pytest.mark.parametrize("provider", ["slack", "teams"])
def test_rendered_payload_matches_hello_world_snapshot(
    provider: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = _load_script(provider, monkeypatch)
    build_payload = cast(Callable[[], dict[str, object]], namespace["build_payload"])
    with (_VECTOR_DIRECTORY / f"{provider}.expected.json").open(
        encoding="utf-8"
    ) as file:
        expected = json.load(file)

    assert build_payload() == expected


@pytest.mark.parametrize(
    ("provider", "destination_url", "expected_status"),
    [
        ("slack", "https://hooks.slack.example/services/test", 200),
        ("teams", "https://workflow.teams.example/hooks/test", 202),
    ],
)
def test_send_posts_json_with_a_bounded_timeout(
    provider: str,
    destination_url: str,
    expected_status: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = _load_script(provider, monkeypatch)
    send = cast(Send, namespace["send"])
    captured_requests: list[urllib.request.Request] = []

    def open_request(
        request: urllib.request.Request,
        *,
        timeout: float,
    ) -> StubResponse:
        assert timeout == 10.0
        captured_requests.append(request)
        return StubResponse(expected_status)

    monkeypatch.setattr(urllib.request, "urlopen", open_request)

    assert send(destination_url) == expected_status
    assert len(captured_requests) == 1
    request = captured_requests[0]
    assert request.get_method() == "POST"
    assert request.full_url == destination_url
    assert request.get_header("Content-type") == "application/json"
    request_data = request.data
    assert isinstance(request_data, bytes)
    assert json.loads(request_data) == json.loads(
        (_VECTOR_DIRECTORY / f"{provider}.expected.json").read_text()
    )


@pytest.mark.parametrize("provider", ["slack", "teams"])
def test_send_rejects_non_https_destinations(
    provider: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = _load_script(provider, monkeypatch)
    send = cast(Send, namespace["send"])

    with pytest.raises(ValueError, match="must be an HTTPS URL"):
        send("http://provider.example/hooks/test")


def test_raw_teams_logic_app_payload_extracts_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = _load_script("teams", monkeypatch)
    build_logic_app_payload = cast(
        Callable[[str, str], dict[str, object]],
        namespace["build_logic_app_payload"],
    )

    payload = build_logic_app_payload("team-example", "channel-example")

    assert payload["teamId"] == "team-example"
    assert payload["channelId"] == "channel-example"
    assert payload["eventId"] == "example-http-001"
    card = payload["card"]
    assert isinstance(card, dict)
    assert card["type"] == "AdaptiveCard"
