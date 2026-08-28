"""Slack channel and broad mention policy tests."""

import pytest

from pyhookkit.adapters.outbound.slack.mention_policy import (
    SlackBroadcastAudience,
    SlackBroadcastNotAllowedError,
    render_slack_broadcast,
    render_slack_channel_link,
)


def test_channel_link_uses_stable_identifier() -> None:
    assert render_slack_channel_link("C00000001") == "<#C00000001>"


def test_broadcast_requires_explicit_audience_allowlist() -> None:
    with pytest.raises(SlackBroadcastNotAllowedError):
        render_slack_broadcast(
            SlackBroadcastAudience.CHANNEL,
            allowed=frozenset(),
        )

    assert (
        render_slack_broadcast(
            SlackBroadcastAudience.HERE,
            allowed=frozenset({SlackBroadcastAudience.HERE}),
        )
        == "<!here>"
    )


@pytest.mark.parametrize("channel_id", ["general", "C invalid", "U00000001"])
def test_channel_link_rejects_invalid_identifiers(channel_id: str) -> None:
    with pytest.raises(ValueError, match="channel identifier"):
        render_slack_channel_link(channel_id)
