# Scenarios

These paired scenarios compose the existing canonical domain and provider
renderers. Each sibling `slack.py` and `teams.py` imports the same
`example_notification.py`.

| Scenario | Required meaning and action |
|---|---|
| `deployment_result` | result, service, environment, revision, duration, time, deployment link |
| `incident_alert_acknowledgment` | severity, incident, service, start, status, responder, acknowledgment and runbook links |
| `approval_request` | subject, requester, deadline, approver, review link |
| `maintenance_notice` | window, affected services, impact, owner, status-page link |

Run a renderer from `examples/python`:

```console
uv run python scenarios/deployment_result/slack.py
uv run python scenarios/deployment_result/teams.py
```

Substitute any other directory in the table. Slack scripts render by default;
`--send` deliberately delivers through the configured Incoming Webhook. They
use `SlackMessageRenderer`, with synthetic identity mappings where a native
mention is required. Delivery needs only an Incoming Webhook URL; the links
are navigation buttons and do not need an interactive callback.

Teams scripts use `TeamsMessageRenderer` and target a Teams Workflow webhook.
No Graph permission is required. The renderer produces Adaptive Card 1.4
headings, severity colors, facts, images, source context, and `Action.OpenUrl`
buttons. User aliases can map to native Teams mention entities. Logical group
mentions remain visible but explicitly report that Workflow group notification
is unavailable. Live sends also resolve each scenario's distinct Microsoft
sample hero image from `EXAMPLE_ASSET_BASE_URL` or the compatible
`TEAMS_ASSET_BASE_URL` fallback.

The top-level canonical body remains the card's fallback text so required
meaning survives hosts that cannot render one of the rich elements.

Teams scripts render by default and accept `--send` for deliberate delivery:

```console
uv run python scenarios/deployment_result/teams.py --send
```

Use the same renderer through the Azure Logic App adapter:

```console
uv run python scenarios/deployment_result/teams.py --send-logic-app
```

The Logic App adapter extracts the inner Adaptive Card and wraps it with the
configured Team and channel IDs. Replacing only the endpoint is not sufficient
because Power Automate Workflow and Logic App triggers accept different request
contracts.

`TEAMS_WORKFLOW_URL` should reference the from-blank flow documented in the
Teams Workflows runbook when template attribution is not acceptable.

All names, IDs, routes, timestamps, and URLs are synthetic.
