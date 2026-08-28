"""Render a Slack thread reply using a synthetic parent reference."""

import json

from example_notification import build_notification

from pyhookkit.adapters.outbound.slack.message_reference import (
    SlackMessageReference,
)
from pyhookkit.adapters.outbound.slack.message_renderer import (
    SlackMessageRenderer,
)
from pyhookkit.adapters.outbound.slack.thread_renderer import (
    SlackThreadRenderer,
)


def main() -> None:
    parent = SlackMessageReference("C00000001", "1724811000.000001")
    payload = SlackThreadRenderer(SlackMessageRenderer()).render(
        build_notification(),
        parent,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
