"""Slack workspace, conversation, and identity discovery."""

from dataclasses import dataclass

from pyhookkit.adapters.outbound.slack.pagination import (
    collect_slack_items,
    collect_slack_strings,
)
from pyhookkit.adapters.outbound.slack.web_api import SlackWebApi
from pyhookkit.json_types import JsonObject


class SlackDirectoryError(ValueError):
    """Slack directory data is missing, malformed, or ambiguous."""


@dataclass(frozen=True, slots=True)
class SlackWorkspace:
    team_id: str
    team_name: str
    user_id: str


@dataclass(frozen=True, slots=True)
class SlackChannel:
    identifier: str
    name: str
    is_private: bool
    is_archived: bool
    is_member: bool


@dataclass(frozen=True, slots=True)
class SlackUser:
    identifier: str
    display_name: str
    real_name: str
    deleted: bool
    is_bot: bool


@dataclass(frozen=True, slots=True)
class SlackUserGroup:
    identifier: str
    handle: str
    name: str


class SlackWorkspaceDirectory:
    """Read only the workspace identity data needed by examples."""

    def __init__(self, api: SlackWebApi) -> None:
        self._api = api

    def workspace(self) -> SlackWorkspace:
        response = self._api.call("auth.test")
        return SlackWorkspace(
            team_id=_required_string(response, "team_id", "auth.test"),
            team_name=_required_string(response, "team", "auth.test"),
            user_id=_required_string(response, "user_id", "auth.test"),
        )

    def channels(self) -> tuple[SlackChannel, ...]:
        items = collect_slack_items(
            self._api,
            method="conversations.list",
            collection_key="channels",
            parameters={
                "types": "public_channel,private_channel",
                "exclude_archived": True,
                "limit": 200,
            },
        )
        return tuple(_channel(item) for item in items)

    def channel_members(self, channel_id: str) -> tuple[str, ...]:
        return collect_slack_strings(
            self._api,
            method="conversations.members",
            collection_key="members",
            parameters={"channel": channel_id, "limit": 200},
        )

    def users(self) -> tuple[SlackUser, ...]:
        items = collect_slack_items(
            self._api,
            method="users.list",
            collection_key="members",
            parameters={"limit": 200},
        )
        return tuple(_user(item) for item in items)

    def user_groups(self) -> tuple[SlackUserGroup, ...]:
        response = self._api.call("usergroups.list", {"include_users": False})
        groups = response.get("usergroups")
        if not isinstance(groups, list):
            raise SlackDirectoryError(
                "Slack usergroups.list response must contain usergroups"
            )
        parsed: list[SlackUserGroup] = []
        for item in groups:
            if not isinstance(item, dict):
                raise SlackDirectoryError(
                    "Slack usergroups.list returned a malformed group"
                )
            parsed.append(_user_group(item))
        return tuple(parsed)

    def find_active_user(self, display_name: str) -> SlackUser:
        target = display_name.casefold()
        matches: list[SlackUser] = []
        for user in self.users():
            names = {user.display_name.casefold(), user.real_name.casefold()}
            if not user.deleted and not user.is_bot and target in names:
                matches.append(user)
        if not matches:
            raise SlackDirectoryError("Slack user was not found")
        if len(matches) > 1:
            raise SlackDirectoryError("Slack user lookup is ambiguous")
        return matches[0]

    def find_user_group(self, handle: str) -> SlackUserGroup:
        target = handle.removeprefix("@").casefold()
        matches: list[SlackUserGroup] = []
        for group in self.user_groups():
            if group.handle.casefold() == target:
                matches.append(group)
        if not matches:
            raise SlackDirectoryError("Slack user group was not found")
        if len(matches) > 1:
            raise SlackDirectoryError("Slack user group lookup is ambiguous")
        return matches[0]


def _channel(item: JsonObject) -> SlackChannel:
    return SlackChannel(
        identifier=_required_string(item, "id", "conversations.list"),
        name=_required_string(item, "name", "conversations.list"),
        is_private=_optional_boolean(item, "is_private"),
        is_archived=_optional_boolean(item, "is_archived"),
        is_member=_optional_boolean(item, "is_member"),
    )


def _user(item: JsonObject) -> SlackUser:
    profile = item.get("profile")
    if not isinstance(profile, dict):
        raise SlackDirectoryError("Slack users.list user must contain a profile")
    display_name = profile.get("display_name")
    real_name = profile.get("real_name")
    return SlackUser(
        identifier=_required_string(item, "id", "users.list"),
        display_name=display_name if isinstance(display_name, str) else "",
        real_name=real_name if isinstance(real_name, str) else "",
        deleted=_optional_boolean(item, "deleted"),
        is_bot=_optional_boolean(item, "is_bot"),
    )


def _user_group(item: JsonObject) -> SlackUserGroup:
    return SlackUserGroup(
        identifier=_required_string(item, "id", "usergroups.list"),
        handle=_required_string(item, "handle", "usergroups.list"),
        name=_required_string(item, "name", "usergroups.list"),
    )


def _required_string(item: JsonObject, key: str, method: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise SlackDirectoryError(f"Slack {method} response requires {key}")
    return value


def _optional_boolean(item: JsonObject, key: str) -> bool:
    value = item.get(key, False)
    if not isinstance(value, bool):
        raise SlackDirectoryError(f"Slack directory field {key} must be boolean")
    return value
