"""Parse a verified Slack approval block action."""

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import cast
from urllib.parse import parse_qs


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class SlackApprovalInteraction:
    decision: ApprovalDecision
    event_id: str
    user_id: str
    channel_id: str
    message_ts: str


class SlackInteractionPayloadError(ValueError):
    """A Slack interaction payload is malformed or unsupported."""


def parse_slack_approval(body: bytes) -> SlackApprovalInteraction:
    parameters = parse_qs(body.decode(), strict_parsing=True)
    encoded_payload = parameters.get("payload")
    if encoded_payload is None or len(encoded_payload) != 1:
        raise SlackInteractionPayloadError(
            "Slack interaction body requires one payload"
        )
    try:
        value: object = json.loads(encoded_payload[0])
    except json.JSONDecodeError:
        raise SlackInteractionPayloadError(
            "Slack interaction payload must be JSON"
        ) from None
    if not isinstance(value, dict):
        raise SlackInteractionPayloadError(
            "Slack interaction payload must be an object"
        )
    payload = cast(dict[object, object], value)
    if payload.get("type") != "block_actions":
        raise SlackInteractionPayloadError("unsupported Slack interaction type")
    actions_value = payload.get("actions")
    if not isinstance(actions_value, list):
        raise SlackInteractionPayloadError("Slack approval requires exactly one action")
    actions = cast(list[object], actions_value)
    if len(actions) != 1:
        raise SlackInteractionPayloadError("Slack approval requires exactly one action")
    action_value = actions[0]
    if not isinstance(action_value, dict):
        raise SlackInteractionPayloadError("Slack approval action must be an object")
    action = cast(dict[object, object], action_value)
    action_id = action.get("action_id")
    if not isinstance(action_id, str):
        raise SlackInteractionPayloadError("Slack approval requires an action ID")
    decision = {
        "approval_approve": ApprovalDecision.APPROVED,
        "approval_reject": ApprovalDecision.REJECTED,
    }.get(action_id)
    if decision is None:
        raise SlackInteractionPayloadError("unsupported Slack approval action")
    return SlackApprovalInteraction(
        decision=decision,
        event_id=_nested_string(action, "value"),
        user_id=_nested_string(payload, "user", "id"),
        channel_id=_nested_string(payload, "channel", "id"),
        message_ts=_nested_string(payload, "message", "ts"),
    )


def _nested_string(
    value: dict[object, object],
    key: str,
    nested_key: str | None = None,
) -> str:
    candidate = value.get(key)
    if nested_key is not None:
        if not isinstance(candidate, dict):
            raise SlackInteractionPayloadError(
                f"Slack interaction requires {key}.{nested_key}"
            )
        candidate = cast(dict[object, object], candidate).get(nested_key)
    if not isinstance(candidate, str) or not candidate:
        suffix = key if nested_key is None else f"{key}.{nested_key}"
        raise SlackInteractionPayloadError(f"Slack interaction requires {suffix}")
    return candidate
