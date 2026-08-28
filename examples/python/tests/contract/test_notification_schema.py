"""Canonical notification schema tests."""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.protocols import Validator

from pyhookkit.adapters.outbound.canonical_notification_json import (
    canonical_notification_to_json,
)
from pyhookkit.domain.notification import (
    CanonicalNotification,
    Link,
    Severity,
)

type JsonObject = dict[str, Any]

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_PATH = _REPOSITORY_ROOT / "contracts" / "notification.schema.json"
_DELIVERY_SCHEMA_PATH = _REPOSITORY_ROOT / "contracts" / "delivery-result.schema.json"
_FUNDAMENTALS_PATH = _REPOSITORY_ROOT / "contracts" / "test-vectors" / "fundamentals"
_NOTIFICATION_PATHS = tuple(sorted(_FUNDAMENTALS_PATH.glob("*/notification.json")))
_HELLO_WORLD_PATH = _FUNDAMENTALS_PATH / "hello-world" / "notification.json"


def _load_json(path: Path) -> JsonObject:
    with path.open(encoding="utf-8") as file:
        value: object = json.load(file)
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    mapping = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in mapping):
        raise TypeError(f"{path} must contain only string keys")
    return cast(JsonObject, mapping)


def _validator(*, check_formats: bool = False) -> Validator:
    format_checker = FormatChecker() if check_formats else None
    return Draft202012Validator(
        _load_json(_SCHEMA_PATH),
        format_checker=format_checker,
    )


def _delivery_validator() -> Validator:
    return Draft202012Validator(_load_json(_DELIVERY_SCHEMA_PATH))


def test_notification_schema_is_valid() -> None:
    Draft202012Validator.check_schema(_load_json(_SCHEMA_PATH))


def test_delivery_result_schema_and_vectors_are_valid() -> None:
    schema = _load_json(_DELIVERY_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    vector_directory = _FUNDAMENTALS_PATH / "error-and-retry"

    _delivery_validator().validate(
        _load_json(vector_directory / "delivery.succeeded.json")
    )
    _delivery_validator().validate(
        _load_json(vector_directory / "delivery.failed.json")
    )


@pytest.mark.parametrize(
    "notification_path",
    _NOTIFICATION_PATHS,
    ids=lambda path: path.parent.name,
)
def test_fundamental_matches_notification_schema(
    notification_path: Path,
) -> None:
    _validator(check_formats=True).validate(_load_json(notification_path))


def test_notification_rejects_unknown_properties() -> None:
    notification = _load_json(_HELLO_WORLD_PATH)
    notification["provider"] = "slack"

    errors = list(_validator().iter_errors(notification))

    assert len(errors) == 1
    assert errors[0].validator == "additionalProperties"


def test_notification_rejects_insecure_image_url() -> None:
    notification = _load_json(_FUNDAMENTALS_PATH / "image" / "notification.json")
    image = cast(JsonObject, notification["image"])
    image["url"] = "http://images.example.com/status.png"

    errors = list(_validator(check_formats=True).iter_errors(notification))

    assert {error.validator for error in errors} == {"pattern"}


def test_domain_notification_serializes_to_contract() -> None:
    notification = CanonicalNotification(
        schema_version="1.0",
        event_id="a" * 128,
        route="a" * 64,
        title="a" * 150,
        body="a" * 8000,
        severity=Severity.INFO,
        links=(Link("a" * 75, "https://example.com"),),
        thread_key="a" * 128,
        metadata={"source": "a" * 64, "correlationId": "a" * 128},
    )

    _validator(check_formats=True).validate(
        canonical_notification_to_json(notification)
    )
