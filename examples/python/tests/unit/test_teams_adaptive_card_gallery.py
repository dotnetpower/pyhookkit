"""Teams Adaptive Card gallery structure and runner tests."""

import json
import os
import subprocess
import sys
from pathlib import Path
from struct import unpack
from typing import cast
from urllib.parse import urlsplit

import pytest

from pyhookkit.entrypoints.teams_card_assets import (
    TeamsAssetConfigurationError,
    teams_asset_replacements,
)
from pyhookkit.entrypoints.teams_card_example import load_teams_card
from pyhookkit.json_types import JsonObject, JsonValue

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_PYTHON_ROOT = _REPOSITORY_ROOT / "examples" / "python"
_GALLERY_ROOT = _PYTHON_ROOT / "teams_adaptive_cards"
_EXAMPLES = (
    "00_visual_hierarchy",
    "01_metrics_dashboard",
    "02_hero_image",
    "03_progressive_disclosure",
    "04_user_mention",
    "05_progress_timeline",
    "06_image_gallery",
)
_ASSETS = (
    "adaptive-card-cat-hero.png",
    "adaptive-card-cat-glasses.png",
    "adaptive-card-cat-portrait.png",
)
_SUPPORTED_WEBHOOK_ACTIONS = {
    "Action.OpenUrl",
    "Action.ToggleVisibility",
}


def _card(example: str) -> JsonObject:
    payload = load_teams_card(_GALLERY_ROOT / example / "card.json")
    attachments = cast(list[JsonValue], payload["attachments"])
    attachment = cast(JsonObject, attachments[0])
    return cast(JsonObject, attachment["content"])


def _objects(value: JsonValue) -> tuple[JsonObject, ...]:
    objects: list[JsonObject] = []
    if isinstance(value, dict):
        objects.append(value)
        for item in value.values():
            objects.extend(_objects(item))
    elif isinstance(value, list):
        for item in value:
            objects.extend(_objects(item))
    return tuple(objects)


@pytest.mark.parametrize("example", _EXAMPLES)
def test_gallery_card_follows_compatible_accessible_baseline(
    example: str,
) -> None:
    card = _card(example)

    assert card["version"] == "1.4"
    assert isinstance(card["fallbackText"], str)
    assert isinstance(card["speak"], str)
    assert card["fallbackText"]
    assert card["speak"]

    for item in _objects(card):
        item_type = item.get("type")
        if item_type == "ColumnSet":
            columns = item.get("columns")
            assert isinstance(columns, list)
            assert len(columns) <= 3
        if item_type == "Column":
            width = item.get("width")
            assert width in (None, "auto", "stretch")
        if item_type == "Image":
            url = item.get("url")
            alt_text = item.get("altText")
            assert isinstance(url, str)
            assert urlsplit(url).scheme == "https"
            assert isinstance(alt_text, str) and alt_text
        if isinstance(item_type, str) and item_type.startswith("Action."):
            assert item_type in _SUPPORTED_WEBHOOK_ACTIONS


@pytest.mark.parametrize("example", _EXAMPLES)
def test_gallery_runner_renders_committed_card(example: str) -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(_PYTHON_ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "teams.py"],
        cwd=_GALLERY_ROOT / example,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == load_teams_card(
        _GALLERY_ROOT / example / "card.json"
    )


def test_user_mention_markers_are_replaced_after_json_parsing() -> None:
    payload = load_teams_card(
        _GALLERY_ROOT / "04_user_mention" / "card.json",
        replacements={
            "{{TEAMS_TEST_USER_ID}}": "example-owner@pyhookkit.example",
            "{{TEAMS_TEST_USER_NAME}}": "Example Owner",
        },
    )
    serialized = json.dumps(payload)

    assert "{{TEAMS_TEST_USER" not in serialized
    assert "<at>Example Owner</at>" in serialized
    assert "example-owner@pyhookkit.example" in serialized


def test_gallery_limits_top_level_actions() -> None:
    for example in _EXAMPLES:
        actions = _card(example).get("actions", [])
        assert isinstance(actions, list)
        assert len(actions) <= 3


def test_mention_runner_rejects_markup_in_display_name() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(_PYTHON_ROOT / "src")
    environment["TEAMS_TEST_USER_ID"] = "example-owner@pyhookkit.example"
    environment["TEAMS_TEST_USER_NAME"] = "Example <Owner>"
    completed = subprocess.run(
        [sys.executable, "teams.py", "--send"],
        cwd=_GALLERY_ROOT / "04_user_mention",
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "markup characters" in completed.stderr


def test_asset_base_resolves_committed_filename() -> None:
    replacements = teams_asset_replacements(
        ("adaptive-card-cat-hero.png",),
        environment={
            "TEAMS_ASSET_BASE_URL": (
                "https://raw.githubusercontent.example/project/assets"
            )
        },
    )

    assert replacements == {
        "https://assets.pyhookkit.example/adaptive-card-cat-hero.png": (
            "https://raw.githubusercontent.example/project/assets/"
            "adaptive-card-cat-hero.png"
        )
    }


@pytest.mark.parametrize(
    "base_url",
    ["", "http://example.com/assets", "https://example.com/assets?token=value"],
)
def test_asset_base_rejects_invalid_urls(base_url: str) -> None:
    with pytest.raises(TeamsAssetConfigurationError):
        teams_asset_replacements(
            ("adaptive-card-cat-hero.png",),
            environment={"TEAMS_ASSET_BASE_URL": base_url},
        )


@pytest.mark.parametrize("filename", _ASSETS)
def test_committed_image_is_teams_compatible_and_attributed(
    filename: str,
) -> None:
    asset_path = _GALLERY_ROOT / "assets" / filename
    content = asset_path.read_bytes()
    width, height = unpack(">II", content[16:24])
    attribution = (_GALLERY_ROOT / "assets" / "ATTRIBUTION.md").read_text()

    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(content) < 1_000_000
    assert width <= 1024
    assert height <= 1024
    assert filename in attribution
    assert "CC BY 4.0" in attribution
