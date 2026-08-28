"""Render Slack Web API update and delete request bodies."""

import json

from example_notification import build_notification

from pyhookkit.adapters.outbound.slack.message_reference import (
    SlackMessageReference,
)
from pyhookkit.adapters.outbound.slack.message_renderer import (
    SlackMessageRenderer,
)
from pyhookkit.adapters.outbound.slack.mutation_renderer import (
    SlackMutationRenderer,
)


def main() -> None:
    reference = SlackMessageReference("C00000001", "1724811000.000001")
    renderer = SlackMutationRenderer(SlackMessageRenderer())
    payloads = {
        "chat.update": renderer.render_update(reference, build_notification()),
        "chat.delete": renderer.render_delete(reference),
    }
    print(json.dumps(payloads, indent=2))


if __name__ == "__main__":
    main()
