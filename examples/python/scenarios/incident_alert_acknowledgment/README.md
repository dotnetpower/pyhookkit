# Incident alert and acknowledgment

This paired scenario reports an active incident and provides acknowledgment and
runbook actions.

## Required meaning

- error severity, incident ID, and affected service;
- start time and acknowledgment state;
- logical responder group;
- acknowledgment and runbook URLs;
- a stable incident correlation and thread key.

The canonical fixture is under
[`contracts/test-vectors/scenarios/incident-alert-acknowledgment`](../../../../contracts/test-vectors/scenarios/incident-alert-acknowledgment).
Reusable construction belongs to
[`application/scenarios/incident_alert_acknowledgment.py`](../../src/pyhookkit/application/scenarios/incident_alert_acknowledgment.py).

## Provider behavior

Slack can map the group alias to a native user-group mention. A Teams Workflow
cannot mention a group directly. The standard example renders an explicit
configuration notice; compact operational delivery may hide that notice while
retaining the responder in canonical fallback text.

Incoming Teams Workflows cannot post a true thread reply. The incident action
therefore opens the external incident record. In the integrated scenario,
GitLab Issues is the acknowledgment system of record.

## Run

From `examples/python`:

```shell
uv run python scenarios/incident_alert_acknowledgment/slack.py
uv run python scenarios/incident_alert_acknowledgment/teams.py
```

The integrated AKS probe deliberately requests an invalid Bookinfo path, builds
this canonical event, and succeeds only after GitLab accepts the notification
pipeline request.
