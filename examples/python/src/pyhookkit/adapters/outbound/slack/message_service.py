"""Slack Web API message lifecycle operations."""

from dataclasses import dataclass
from datetime import datetime

from pyhookkit.adapters.outbound.slack.message_reference import (
    SlackMessageReference,
)
from pyhookkit.adapters.outbound.slack.web_api import SlackWebApi
from pyhookkit.json_types import JsonObject


class SlackMessageResponseError(ValueError):
    """A Slack message response lacks a usable reference."""


@dataclass(frozen=True, slots=True)
class SlackScheduledMessage:
    channel_id: str
    scheduled_message_id: str
    post_at: int


class SlackMessageService:
    """Perform lifecycle operations for messages authored by the Slack app."""

    def __init__(self, api: SlackWebApi) -> None:
        self._api = api

    def post(
        self,
        channel_id: str,
        payload: JsonObject,
        *,
        parent: SlackMessageReference | None = None,
    ) -> SlackMessageReference:
        request = dict(payload)
        request["channel"] = channel_id
        if parent is not None:
            if parent.channel_id != channel_id:
                raise ValueError(
                    "Slack thread parent must belong to the target channel"
                )
            request["thread_ts"] = parent.message_ts
        response = self._api.call("chat.postMessage", request)
        return _message_reference(response)

    def update(
        self,
        reference: SlackMessageReference,
        payload: JsonObject,
    ) -> SlackMessageReference:
        request = dict(payload)
        request.update({"channel": reference.channel_id, "ts": reference.message_ts})
        response = self._api.call("chat.update", request)
        return _message_reference(response, fallback_channel=reference.channel_id)

    def delete(self, reference: SlackMessageReference) -> None:
        self._api.call(
            "chat.delete",
            {"channel": reference.channel_id, "ts": reference.message_ts},
        )

    def post_ephemeral(
        self,
        channel_id: str,
        user_id: str,
        payload: JsonObject,
    ) -> str:
        request = dict(payload)
        request.update({"channel": channel_id, "user": user_id})
        response = self._api.call("chat.postEphemeral", request)
        return _required_string(response, "message_ts", "chat.postEphemeral")

    def schedule(
        self,
        channel_id: str,
        post_at: datetime,
        payload: JsonObject,
    ) -> SlackScheduledMessage:
        if post_at.utcoffset() is None:
            raise ValueError("scheduled Slack time must include a UTC offset")
        request = dict(payload)
        request.update({"channel": channel_id, "post_at": int(post_at.timestamp())})
        response = self._api.call("chat.scheduleMessage", request)
        return SlackScheduledMessage(
            channel_id=_required_string(response, "channel", "chat.scheduleMessage"),
            scheduled_message_id=_required_string(
                response, "scheduled_message_id", "chat.scheduleMessage"
            ),
            post_at=int(post_at.timestamp()),
        )

    def delete_scheduled(self, message: SlackScheduledMessage) -> None:
        self._api.call(
            "chat.deleteScheduledMessage",
            {
                "channel": message.channel_id,
                "scheduled_message_id": message.scheduled_message_id,
            },
        )

    def add_reaction(self, reference: SlackMessageReference, emoji_name: str) -> None:
        _require_emoji_name(emoji_name)
        self._api.call(
            "reactions.add",
            {
                "channel": reference.channel_id,
                "timestamp": reference.message_ts,
                "name": emoji_name,
            },
        )

    def remove_reaction(
        self,
        reference: SlackMessageReference,
        emoji_name: str,
    ) -> None:
        _require_emoji_name(emoji_name)
        self._api.call(
            "reactions.remove",
            {
                "channel": reference.channel_id,
                "timestamp": reference.message_ts,
                "name": emoji_name,
            },
        )


def _message_reference(
    response: JsonObject,
    *,
    fallback_channel: str | None = None,
) -> SlackMessageReference:
    channel = response.get("channel", fallback_channel)
    timestamp = response.get("ts")
    if not isinstance(channel, str) or not isinstance(timestamp, str):
        raise SlackMessageResponseError(
            "Slack message response must contain channel and ts"
        )
    return SlackMessageReference(channel, timestamp)


def _required_string(response: JsonObject, key: str, method: str) -> str:
    value = response.get(key)
    if not isinstance(value, str) or not value:
        raise SlackMessageResponseError(f"Slack {method} response requires {key}")
    return value


def _require_emoji_name(value: str) -> None:
    if not value or ":" in value or any(character.isspace() for character in value):
        raise ValueError("Slack emoji name must omit colons and whitespace")
