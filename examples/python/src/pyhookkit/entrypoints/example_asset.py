"""Resolve public assets used by live notification examples."""

import os
from collections.abc import Mapping
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from pyhookkit.json_types import JsonObject, JsonValue

_PRIMARY_ENVIRONMENT_VARIABLE = "EXAMPLE_ASSET_BASE_URL"
_LEGACY_ENVIRONMENT_VARIABLE = "TEAMS_ASSET_BASE_URL"
_ASSET_MARKER = "https://assets.pyhookkit.example/"


class ExampleAssetConfigurationError(ValueError):
    """The public example asset base URL is missing or invalid."""


def example_asset_url(
    filename: str,
    *,
    environment: Mapping[str, str] | None = None,
) -> str:
    """Build one public example asset URL without exposing notification delivery."""
    filename = _validated_filename(filename)
    active_environment = os.environ if environment is None else environment
    base_url = active_environment.get(_PRIMARY_ENVIRONMENT_VARIABLE, "").strip()
    if not base_url:
        base_url = active_environment.get(_LEGACY_ENVIRONMENT_VARIABLE, "").strip()
    base_url = base_url.rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ExampleAssetConfigurationError(
            f"{_PRIMARY_ENVIRONMENT_VARIABLE} must be an absolute HTTPS URL "
            "without query or fragment"
        )
    return f"{base_url}/{filename}"


def example_asset_marker(filename: str) -> str:
    """Build a synthetic asset URL for committed provider payloads."""
    return f"{_ASSET_MARKER}{_validated_filename(filename)}"


def resolve_example_asset_urls(
    payload: JsonObject,
    *,
    environment: Mapping[str, str] | None = None,
) -> JsonObject:
    """Replace synthetic asset markers only when a payload contains them."""
    return {
        key: _resolve_value(value, environment=environment)
        for key, value in payload.items()
    }


def _resolve_value(
    value: JsonValue,
    *,
    environment: Mapping[str, str] | None,
) -> JsonValue:
    if isinstance(value, str) and value.startswith(_ASSET_MARKER):
        return example_asset_url(
            value.removeprefix(_ASSET_MARKER),
            environment=environment,
        )
    if isinstance(value, list):
        return [_resolve_value(item, environment=environment) for item in value]
    if isinstance(value, dict):
        return {
            key: _resolve_value(item, environment=environment)
            for key, item in value.items()
        }
    return value


def _validated_filename(filename: str) -> str:
    path = PurePosixPath(filename)
    if (
        not filename
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ExampleAssetConfigurationError(
            "example asset filename must be a non-empty relative path"
        )
    return path.as_posix()
