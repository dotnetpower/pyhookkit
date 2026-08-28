"""CLI composition for renderable Microsoft Teams Workflow examples."""

import argparse
import json
import os
from collections.abc import Mapping, Sequence

from pyhookkit.adapters.outbound.delivery_result_json import (
    delivery_result_to_json,
)
from pyhookkit.adapters.outbound.teams.workflow_destination import (
    TeamsWorkflowDestination,
)
from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.domain.delivery import DeliveryState
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.ports.message_renderer import MessageRenderer


def run_teams_workflow_example(
    notification: CanonicalNotification,
    renderer: MessageRenderer,
    *,
    arguments: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Render or deliberately send one Teams Workflow example."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true")
    parsed = parser.parse_args(arguments)
    payload = renderer.render(notification)
    if not parsed.send:
        print(json.dumps(payload, indent=2))
        return

    active_environment = os.environ if environment is None else environment
    raw_url = active_environment.get("TEAMS_WORKFLOW_URL", "").strip()
    if not raw_url:
        raise ValueError("TEAMS_WORKFLOW_URL is required with --send")
    result = TeamsWorkflowDestination(TeamsWorkflowUrl(raw_url)).send(payload)
    print(json.dumps(delivery_result_to_json(result), indent=2))
    if result.state is DeliveryState.FAILED:
        raise SystemExit(1)
