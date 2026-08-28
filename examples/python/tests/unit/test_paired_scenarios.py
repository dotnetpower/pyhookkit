"""Snapshot and semantic-parity tests for paired scenarios."""

import json
import os
import subprocess
import sys
from functools import cache
from pathlib import Path
from typing import cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.protocols import Validator  # pyright: ignore[reportMissingModuleSource]

from pyhookkit.json_types import JsonObject, JsonValue

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_PYTHON_ROOT = _REPOSITORY_ROOT / "examples" / "python"
_VECTOR_ROOT = _REPOSITORY_ROOT / "contracts" / "test-vectors" / "scenarios"
_FUNDAMENTAL_VECTOR_ROOT = (
    _REPOSITORY_ROOT / "contracts" / "test-vectors" / "fundamentals"
)
_SCHEMA_PATH = _REPOSITORY_ROOT / "contracts" / "notification.schema.json"
_SCENARIOS = (
    ("deployment-result", "deployment_result"),
    ("incident-alert-acknowledgment", "incident_alert_acknowledgment"),
    ("approval-request", "approval_request"),
    ("maintenance-notice", "maintenance_notice"),
)
_REQUIRED_SEMANTICS = {
    "deployment-result": (
        "Deployment succeeded",
        "SUCCESS",
        "example-api",
        "staging",
        "9f3a2c1",
        "2m 18s",
        "2026-08-28T03:15:00Z",
        "View deployment",
        "https://deployments.example.com/runs/run-1042",
    ),
    "incident-alert-acknowledgment": (
        "Incident alert: elevated latency",
        "ERROR",
        "INC-204",
        "example-checkout",
        "2026-08-28T04:20:00Z",
        "unacknowledged",
        "example-responders",
        "Acknowledge incident",
        "https://incidents.example.com/incidents/inc-204/acknowledge",
        "Open runbook",
        "https://runbooks.example.com/services/example-checkout/latency",
    ),
    "approval-request": (
        "Approval requested",
        "WARNING",
        "APR-307",
        "example-api 2026.08.28",
        "example-requester",
        "2026-08-28T07:00:00Z",
        "example-approver",
        "Review request",
        "https://approvals.example.com/requests/apr-307",
    ),
    "maintenance-notice": (
        "Scheduled maintenance notice",
        "INFO",
        "example-api",
        "example-worker",
        "2026-08-30T01:00:00Z",
        "2026-08-30T02:00:00Z",
        "Brief request retries",
        "example-operations",
        "Status page",
        "https://status.example.com/notices/maintenance-118",
    ),
}


def _load_json(path: Path) -> JsonObject:
    with path.open(encoding="utf-8") as file:
        value: object = json.load(file)
    json_value = _as_json_value(value, path)
    if not isinstance(json_value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return json_value


def _as_json_value(value: object, path: Path) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        return [_as_json_value(item, path) for item in cast(list[object], value)]
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        if not all(isinstance(key, str) for key in mapping):
            raise TypeError(f"{path} must contain only string keys")
        return {
            cast(str, key): _as_json_value(item, path) for key, item in mapping.items()
        }
    raise TypeError(f"{path} contains a non-JSON value")


def _background_image_urls(value: JsonValue) -> tuple[str, ...]:
    urls: list[str] = []
    if isinstance(value, dict):
        background = value.get("backgroundImage")
        if isinstance(background, dict):
            url = background.get("url")
            if isinstance(url, str):
                urls.append(url)
        for item in value.values():
            urls.extend(_background_image_urls(item))
    elif isinstance(value, list):
        for item in value:
            urls.extend(_background_image_urls(item))
    return tuple(urls)


def _validator() -> Validator:
    return Draft202012Validator(
        _load_json(_SCHEMA_PATH),
        format_checker=FormatChecker(),
    )


@cache
def _render_example(example_name: str, provider: str) -> object:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(_PYTHON_ROOT / "src")
    completed = subprocess.run(
        [sys.executable, f"{provider}.py"],
        cwd=_PYTHON_ROOT / "scenarios" / example_name,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


@cache
def _canonical_example(example_name: str) -> object:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(_PYTHON_ROOT / "src")
    command = (
        "import json; "
        "from example_notification import build_notification; "
        "from pyhookkit.adapters.outbound.canonical_notification_json "
        "import canonical_notification_to_json; "
        "print(json.dumps(canonical_notification_to_json(build_notification())))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=_PYTHON_ROOT / "scenarios" / example_name,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


@pytest.mark.parametrize(
    ("vector_name", "example_name"),
    _SCENARIOS,
    ids=[vector_name for vector_name, _ in _SCENARIOS],
)
def test_scenario_matches_notification_schema(
    vector_name: str,
    example_name: str,
) -> None:
    del example_name
    _validator().validate(_load_json(_VECTOR_ROOT / vector_name / "notification.json"))


@pytest.mark.parametrize(
    ("vector_name", "example_name"),
    _SCENARIOS,
    ids=[vector_name for vector_name, _ in _SCENARIOS],
)
def test_examples_use_the_canonical_scenario(
    vector_name: str,
    example_name: str,
) -> None:
    assert _canonical_example(example_name) == _load_json(
        _VECTOR_ROOT / vector_name / "notification.json"
    )


@pytest.mark.parametrize(
    ("vector_name", "example_name"),
    _SCENARIOS,
    ids=[vector_name for vector_name, _ in _SCENARIOS],
)
@pytest.mark.parametrize("provider", ("slack", "teams"))
def test_scenario_render_matches_provider_snapshot(
    vector_name: str,
    example_name: str,
    provider: str,
) -> None:
    assert _render_example(example_name, provider) == _load_json(
        _VECTOR_ROOT / vector_name / f"{provider}.expected.json"
    )


@pytest.mark.parametrize(
    ("vector_name", "example_name"),
    _SCENARIOS,
    ids=[vector_name for vector_name, _ in _SCENARIOS],
)
def test_scenario_renderers_preserve_required_semantics(
    vector_name: str,
    example_name: str,
) -> None:
    slack_payload = json.dumps(_render_example(example_name, "slack"))
    teams_payload = json.dumps(_render_example(example_name, "teams"))

    for semantic_value in _REQUIRED_SEMANTICS[vector_name]:
        assert semantic_value in slack_payload
        assert semantic_value in teams_payload


def test_paired_teams_examples_use_distinct_hero_images() -> None:
    payloads = [
        _load_json(_FUNDAMENTAL_VECTOR_ROOT / capability / "teams.expected.json")
        for capability in ("rich-card", "image")
    ]
    payloads.extend(
        _load_json(_VECTOR_ROOT / vector_name / "teams.expected.json")
        for vector_name, _ in _SCENARIOS
    )

    hero_urls = [url for payload in payloads for url in _background_image_urls(payload)]

    assert len(hero_urls) == len(payloads)
    assert len(set(hero_urls)) == len(payloads)
