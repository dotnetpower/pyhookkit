"""Adapt a Teams Workflow envelope to the Logic App post-card contract."""

from dataclasses import dataclass
from typing import cast

from pyhookkit.json_types import JsonObject, JsonValue


class TeamsLogicAppRequestError(ValueError):
    """A Teams payload cannot be adapted to the Logic App contract."""


@dataclass(frozen=True, slots=True)
class TeamsLogicAppTarget:
    """Provider identifiers required by the Logic App Teams connector."""

    team_id: str
    channel_id: str

    def __post_init__(self) -> None:
        if not self.team_id.strip():
            raise TeamsLogicAppRequestError("Logic App team ID must not be blank")
        if not self.channel_id.strip():
            raise TeamsLogicAppRequestError("Logic App channel ID must not be blank")


def build_teams_logic_app_request(
    envelope: JsonObject,
    target: TeamsLogicAppTarget,
    *,
    event_id: str | None = None,
) -> JsonObject:
    """Extract the Adaptive Card and add Logic App destination routing."""
    card = _adaptive_card(envelope)
    request: JsonObject = {
        "teamId": target.team_id,
        "channelId": target.channel_id,
        "card": card,
    }
    if event_id is not None:
        if not event_id.strip():
            raise TeamsLogicAppRequestError("Logic App event ID must not be blank")
        request["eventId"] = event_id
    return request


def _adaptive_card(envelope: JsonObject) -> JsonObject:
    attachments = envelope.get("attachments")
    if not isinstance(attachments, list) or len(attachments) != 1:
        raise TeamsLogicAppRequestError(
            "Teams envelope must contain exactly one Adaptive Card attachment"
        )
    attachment_value: JsonValue = attachments[0]
    if not isinstance(attachment_value, dict):
        raise TeamsLogicAppRequestError("Teams attachment must be an object")
    attachment = cast(JsonObject, attachment_value)
    if attachment.get("contentType") != "application/vnd.microsoft.card.adaptive":
        raise TeamsLogicAppRequestError("Teams attachment must be an Adaptive Card")
    card_value = attachment.get("content")
    if (
        not isinstance(card_value, dict)
        or card_value.get("type") != "AdaptiveCard"
        or not isinstance(card_value.get("version"), str)
        or not isinstance(card_value.get("body"), list)
        or not card_value["body"]
    ):
        raise TeamsLogicAppRequestError("Teams Adaptive Card content is incomplete")
    return cast(JsonObject, card_value)
