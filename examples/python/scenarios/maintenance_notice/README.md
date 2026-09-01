# Maintenance notice

This paired scenario announces a bounded maintenance window and expected
service impact.

## Required meaning

- informational severity;
- start and end of the window;
- affected services;
- expected impact;
- logical owner group;
- one status action.

The canonical fixture is under
[`contracts/test-vectors/scenarios/maintenance-notice`](../../../../contracts/test-vectors/scenarios/maintenance-notice).
Reusable construction belongs to
[`application/scenarios/maintenance_notice.py`](../../src/pyhookkit/application/scenarios/maintenance_notice.py).

## Provider behavior

Slack can map the owner alias to a native user-group mention. Teams Workflow
group notification requires Microsoft Graph member expansion or a bot. The
standard Teams example reports that difference. The integrated GitLab job uses
compact presentation and keeps GitLab as the operational ownership system.

Both providers preserve the window, service list, impact, owner alias, and
status URL in the canonical fallback.

## Run

From `examples/python`:

```shell
uv run python scenarios/maintenance_notice/slack.py
uv run python scenarios/maintenance_notice/teams.py
```

The integrated scenario uses a disabled-by-default GitLab schedule with
`action=maintenance-notice`. The live card links to the exact pipeline rather
than a generic status-page placeholder.
