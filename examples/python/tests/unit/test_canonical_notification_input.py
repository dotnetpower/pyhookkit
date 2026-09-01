"""Canonical notification JSON input adapter tests."""

import json
from pathlib import Path
from typing import cast

import pytest

from pyhookkit.adapters.inbound.canonical_notification_json import (
    CanonicalNotificationJsonError,
    canonical_notification_from_json,
    load_canonical_notification,
)
from pyhookkit.adapters.outbound.canonical_notification_json import (
    canonical_notification_to_json,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_SCENARIO_VECTORS = _REPOSITORY_ROOT / "contracts" / "test-vectors" / "scenarios"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_loader_round_trips_committed_notification_json() -> None:
    path = _SCENARIO_VECTORS / "deployment-result" / "notification.json"

    notification = load_canonical_notification(path)

    assert canonical_notification_to_json(notification) == _load_json(path)


def test_loader_rejects_unknown_top_level_fields() -> None:
    notification = _load_json(
        _SCENARIO_VECTORS / "deployment-result" / "notification.json"
    )
    assert isinstance(notification, dict)
    payload = cast(dict[str, object], notification)
    payload["provider"] = "slack"

    with pytest.raises(
        CanonicalNotificationJsonError,
        match="contains unsupported fields: provider",
    ):
        canonical_notification_from_json(payload)


def test_loader_rejects_wrong_nested_types() -> None:
    notification = _load_json(
        _SCENARIO_VECTORS / "approval-request" / "notification.json"
    )
    assert isinstance(notification, dict)
    payload = cast(dict[str, object], notification)
    payload["metadata"] = {"source": 7}

    with pytest.raises(
        CanonicalNotificationJsonError,
        match=r"notification\.metadata\.source must be a string",
    ):
        canonical_notification_from_json(payload)
