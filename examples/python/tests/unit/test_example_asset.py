"""Public example asset URL tests."""

import pytest

from pyhookkit.entrypoints.example_asset import (
    ExampleAssetConfigurationError,
    example_asset_marker,
    example_asset_url,
    resolve_example_asset_urls,
)
from pyhookkit.json_types import JsonObject


def test_example_asset_prefers_provider_neutral_configuration() -> None:
    assert (
        example_asset_url(
            "sample.png",
            environment={
                "EXAMPLE_ASSET_BASE_URL": "https://assets.example.com/examples/",
                "TEAMS_ASSET_BASE_URL": "https://legacy.example.com",
            },
        )
        == "https://assets.example.com/examples/sample.png"
    )


def test_example_asset_accepts_existing_teams_configuration() -> None:
    assert (
        example_asset_url(
            "sample.png",
            environment={"TEAMS_ASSET_BASE_URL": "https://assets.example.com"},
        )
        == "https://assets.example.com/sample.png"
    )


def test_example_asset_marker_preserves_relative_path() -> None:
    assert example_asset_marker("samples/editorial/assets/editorialHero.png") == (
        "https://assets.pyhookkit.example/samples/editorial/assets/editorialHero.png"
    )


def test_example_asset_markers_are_replaced_recursively() -> None:
    payload: JsonObject = {
        "type": "message",
        "attachments": [
            {
                "image": "https://assets.pyhookkit.example/editorialHero.png",
                "title": "Synthetic card",
            }
        ],
    }

    assert resolve_example_asset_urls(
        payload,
        environment={"EXAMPLE_ASSET_BASE_URL": "https://assets.example.com"},
    ) == {
        "type": "message",
        "attachments": [
            {
                "image": "https://assets.example.com/editorialHero.png",
                "title": "Synthetic card",
            }
        ],
    }


def test_payload_without_asset_markers_needs_no_asset_configuration() -> None:
    payload: JsonObject = {"type": "message"}

    assert resolve_example_asset_urls(payload, environment={}) == payload


@pytest.mark.parametrize(
    "base_url",
    ["", "http://assets.example.com", "https://assets.example.com?token=value"],
)
def test_example_asset_rejects_invalid_base_url(base_url: str) -> None:
    with pytest.raises(ExampleAssetConfigurationError):
        example_asset_url(
            "sample.png",
            environment={"EXAMPLE_ASSET_BASE_URL": base_url},
        )


@pytest.mark.parametrize("filename", ("", "/sample.png", "../sample.png"))
def test_example_asset_rejects_invalid_relative_path(filename: str) -> None:
    with pytest.raises(ExampleAssetConfigurationError):
        example_asset_marker(filename)
