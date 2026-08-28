"""Verify and parse Slack Events API HTTP requests."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from pyhookkit.adapters.inbound.slack.request_signing import SlackRequestVerifier

_SUPPORTED_EVENT_TYPES = {
    "app_mention",
    "app_uninstalled",
    "message",
    "reaction_added",
    "tokens_revoked",
}


class SlackEventPayloadError(ValueError):
    """A Slack Events API payload is malformed or unsupported."""


@dataclass(frozen=True, slots=True)
class SlackEvent:
    event_id: str
    event_type: str
    team_id: str
    subtype: str | None = None
    user_id: str | None = None
    channel_id: str | None = None


@dataclass(frozen=True, slots=True)
class SlackEventAcknowledgment:
    body: bytes
    event: SlackEvent | None


class SlackEventsHttpHandler:
    """Authenticate a Slack Events API request and build its acknowledgment."""

    def __init__(self, verifier: SlackRequestVerifier) -> None:
        self._verifier = verifier

    def handle(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> SlackEventAcknowledgment:
        normalized = {key.lower(): value for key, value in headers.items()}
        timestamp = normalized.get("x-slack-request-timestamp", "")
        signature = normalized.get("x-slack-signature", "")
        self._verifier.verify(timestamp, signature, body)
        payload = _json_object(body)
        payload_type = payload.get("type")
        if payload_type == "url_verification":
            challenge = payload.get("challenge")
            if not isinstance(challenge, str) or not challenge:
                raise SlackEventPayloadError(
                    "Slack URL verification requires a challenge"
                )
            return SlackEventAcknowledgment(challenge.encode(), None)
        if payload_type != "event_callback":
            raise SlackEventPayloadError("unsupported Slack event envelope")
        event = payload.get("event")
        if not isinstance(event, dict):
            raise SlackEventPayloadError("Slack event callback requires an event")
        event_mapping = cast(dict[object, object], event)
        event_type = _required_object_string(event_mapping, "type")
        if event_type not in _SUPPORTED_EVENT_TYPES:
            raise SlackEventPayloadError("unsupported Slack event type")
        return SlackEventAcknowledgment(
            b"",
            SlackEvent(
                event_id=_required_string(payload, "event_id"),
                event_type=event_type,
                team_id=_required_string(payload, "team_id"),
                subtype=_optional_object_string(event_mapping, "subtype"),
                user_id=_optional_object_string(event_mapping, "user"),
                channel_id=_optional_object_string(event_mapping, "channel"),
            ),
        )


def _json_object(body: bytes) -> dict[object, object]:
    try:
        value: object = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SlackEventPayloadError("Slack event body must be JSON") from None
    if not isinstance(value, dict):
        raise SlackEventPayloadError("Slack event body must be an object")
    return cast(dict[object, object], value)


def _required_string(value: dict[object, object], key: str) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate:
        raise SlackEventPayloadError(f"Slack event envelope requires {key}")
    return candidate


def _required_object_string(value: dict[object, object], key: str) -> str:
    return _required_string(value, key)


def _optional_object_string(
    value: dict[object, object],
    key: str,
) -> str | None:
    candidate = value.get(key)
    if candidate is None:
        return None
    if not isinstance(candidate, str) or not candidate:
        raise SlackEventPayloadError(f"Slack event field {key} must be a string")
    return candidate
