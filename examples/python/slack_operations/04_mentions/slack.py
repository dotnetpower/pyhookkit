"""Render Slack channel links and explicitly authorized broad mentions."""

import argparse
import json

from pyhookkit.adapters.outbound.slack.mention_policy import (
    SlackBroadcastAudience,
    render_slack_broadcast,
    render_slack_channel_link,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel-id", default="C00000001")
    parser.add_argument(
        "--broadcast",
        choices=[audience.value for audience in SlackBroadcastAudience],
    )
    parser.add_argument("--allow-broadcast", action="store_true")
    arguments = parser.parse_args()

    output = {"channelLink": render_slack_channel_link(arguments.channel_id)}
    if arguments.broadcast is not None:
        audience = SlackBroadcastAudience(arguments.broadcast)
        allowed: frozenset[SlackBroadcastAudience] = (
            frozenset({audience}) if arguments.allow_broadcast else frozenset()
        )
        output["broadcast"] = render_slack_broadcast(audience, allowed=allowed)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
