"""Slack workspace directory tests."""

from collections.abc import Mapping
from typing import cast

import pytest

from pyhookkit.adapters.outbound.slack.web_api import SlackWebApi
from pyhookkit.adapters.outbound.slack.workspace_directory import (
    SlackDirectoryError,
    SlackWorkspaceDirectory,
)
from pyhookkit.json_types import JsonObject


class StubApi:
    def __init__(self, responses: list[JsonObject]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, Mapping[str, object] | None]] = []

    def call(
        self,
        method: str,
        payload: Mapping[str, object] | None = None,
    ) -> JsonObject:
        self.calls.append((method, payload))
        return self.responses.pop(0)


def _directory(responses: list[JsonObject]) -> SlackWorkspaceDirectory:
    return SlackWorkspaceDirectory(cast(SlackWebApi, StubApi(responses)))


def test_workspace_returns_redacted_identity_summary() -> None:
    workspace = _directory(
        [
            {
                "ok": True,
                "team_id": "T00000001",
                "team": "Synthetic Workspace",
                "user_id": "U00000001",
            }
        ]
    ).workspace()

    assert workspace.team_name == "Synthetic Workspace"
    assert workspace.team_id == "T00000001"


def test_channels_follow_cursor_pagination() -> None:
    directory = _directory(
        [
            {
                "ok": True,
                "channels": [
                    {
                        "id": "C00000001",
                        "name": "platform-alerts",
                        "is_private": False,
                        "is_archived": False,
                        "is_member": True,
                    }
                ],
                "response_metadata": {"next_cursor": "next"},
            },
            {
                "ok": True,
                "channels": [
                    {
                        "id": "G00000001",
                        "name": "private-alerts",
                        "is_private": True,
                        "is_archived": False,
                        "is_member": True,
                    }
                ],
                "response_metadata": {"next_cursor": ""},
            },
        ]
    )

    channels = directory.channels()

    assert [channel.name for channel in channels] == [
        "platform-alerts",
        "private-alerts",
    ]


def test_channel_members_collects_string_identifiers() -> None:
    directory = _directory(
        [
            {
                "ok": True,
                "members": ["U00000001", "U00000002"],
                "response_metadata": {"next_cursor": ""},
            }
        ]
    )

    assert directory.channel_members("C00000001") == (
        "U00000001",
        "U00000002",
    )


def test_display_name_lookup_excludes_bots_and_deleted_users() -> None:
    directory = _directory(
        [
            {
                "ok": True,
                "members": [
                    {
                        "id": "U00000001",
                        "profile": {
                            "display_name": "example-owner",
                            "real_name": "Example Owner",
                        },
                    },
                    {
                        "id": "U00000002",
                        "deleted": True,
                        "profile": {
                            "display_name": "example-owner",
                            "real_name": "Former Owner",
                        },
                    },
                ],
                "response_metadata": {"next_cursor": ""},
            }
        ]
    )

    assert directory.find_active_user("example-owner").identifier == "U00000001"


def test_user_group_lookup_uses_handle() -> None:
    directory = _directory(
        [
            {
                "ok": True,
                "usergroups": [
                    {
                        "id": "S00000001",
                        "handle": "example-responders",
                        "name": "Example Responders",
                    }
                ],
            }
        ]
    )

    assert directory.find_user_group("@example-responders").identifier == "S00000001"


def test_directory_rejects_missing_and_ambiguous_users() -> None:
    missing = _directory(
        [{"ok": True, "members": [], "response_metadata": {"next_cursor": ""}}]
    )
    with pytest.raises(SlackDirectoryError, match="not found"):
        missing.find_active_user("example-owner")

    ambiguous = _directory(
        [
            {
                "ok": True,
                "members": [
                    {
                        "id": "U00000001",
                        "profile": {
                            "display_name": "same-name",
                            "real_name": "First",
                        },
                    },
                    {
                        "id": "U00000002",
                        "profile": {
                            "display_name": "same-name",
                            "real_name": "Second",
                        },
                    },
                ],
                "response_metadata": {"next_cursor": ""},
            }
        ]
    )
    with pytest.raises(SlackDirectoryError, match="ambiguous"):
        ambiguous.find_active_user("same-name")
