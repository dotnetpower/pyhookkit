"""Slack message lifecycle service tests."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import cast

import pytest

from pyhookkit.adapters.outbound.slack.message_reference import (
    SlackMessageReference,
)
from pyhookkit.adapters.outbound.slack.message_service import SlackMessageService
from pyhookkit.adapters.outbound.slack.web_api import SlackWebApi
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


def _service(responses: list[JsonObject]) -> tuple[SlackMessageService, StubApi]:
    api = StubApi(responses)
    return SlackMessageService(cast(SlackWebApi, api)), api


def test_post_reply_update_delete_lifecycle_retains_references() -> None:
    service, api = _service(
        [
            {"ok": True, "channel": "C00000001", "ts": "1724811000.000001"},
            {"ok": True, "channel": "C00000001", "ts": "1724811001.000002"},
            {"ok": True, "channel": "C00000001", "ts": "1724811000.000001"},
            {"ok": True},
        ]
    )

    parent = service.post("C00000001", {"text": "Synthetic alert"})
    reply = service.post("C00000001", {"text": "Acknowledged"}, parent=parent)
    updated = service.update(parent, {"text": "Synthetic alert resolved"})
    service.delete(reply)

    assert updated == parent
    assert api.calls[1][1] == {
        "text": "Acknowledged",
        "channel": "C00000001",
        "thread_ts": "1724811000.000001",
    }
    assert api.calls[3] == (
        "chat.delete",
        {"channel": "C00000001", "ts": "1724811001.000002"},
    )


def test_thread_parent_must_match_channel() -> None:
    service, _api = _service([])
    parent = SlackMessageReference("C00000001", "1724811000.000001")

    with pytest.raises(ValueError, match="target channel"):
        service.post("C00000002", {"text": "Reply"}, parent=parent)


def test_reaction_ephemeral_and_schedule_operations() -> None:
    service, api = _service(
        [
            {"ok": True},
            {"ok": True},
            {"ok": True, "message_ts": "1724811001.000002"},
            {
                "ok": True,
                "channel": "C00000001",
                "scheduled_message_id": "Q00000001",
            },
            {"ok": True},
        ]
    )
    reference = SlackMessageReference("C00000001", "1724811000.000001")

    service.add_reaction(reference, "hourglass_flowing_sand")
    service.remove_reaction(reference, "hourglass_flowing_sand")
    assert (
        service.post_ephemeral("C00000001", "U00000001", {"text": "Private status"})
        == "1724811001.000002"
    )
    scheduled = service.schedule(
        "C00000001",
        datetime(2030, 1, 1, tzinfo=UTC),
        {"text": "Maintenance starts"},
    )
    service.delete_scheduled(scheduled)

    assert scheduled.scheduled_message_id == "Q00000001"
    assert [method for method, _payload in api.calls] == [
        "reactions.add",
        "reactions.remove",
        "chat.postEphemeral",
        "chat.scheduleMessage",
        "chat.deleteScheduledMessage",
    ]


@pytest.mark.parametrize("emoji", ["", ":white_check_mark:", "two words"])
def test_reaction_rejects_invalid_emoji_names(emoji: str) -> None:
    service, _api = _service([])
    reference = SlackMessageReference("C00000001", "1724811000.000001")

    with pytest.raises(ValueError, match="emoji name"):
        service.add_reaction(reference, emoji)
