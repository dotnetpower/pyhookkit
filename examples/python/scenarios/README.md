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
requires additional Graph member-expansion configuration. Hero labels use a
theme-aware solid overlay for reliable contrast across mixed photography.
Scenario cards use distinct PyHookKit-created static banners with no video
controls or third-party imagery. Their compact visual body avoids repeating the
long canonical fallback; title, severity, facts, mentions, context, and actions
remain visible. Live sends resolve these banners from `EXAMPLE_ASSET_BASE_URL`
or the compatible `TEAMS_ASSET_BASE_URL` fallback.

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

## Automation CLI

CI systems can construct the same scenarios with validated runtime values:

```console
uv run python -m pyhookkit.entrypoints.scenario_cli \
  deployment-result teams \
  --event-id deploy-example-1042 \
  --correlation-id deploy-example-1042 \
  --service bookinfo \
  --deployment-environment staging \
  --revision 9f3a2c1 \
  --duration "2m 18s" \
  --completed-at 2026-08-28T03:15:00Z \
  --deployment-url https://deployments.example.com/runs/1042
```

Add `--send` only for deliberate delivery. The CLI also accepts an existing
canonical contract file:

```console
uv run python -m pyhookkit.entrypoints.scenario_cli \
  --input ../../contracts/test-vectors/scenarios/deployment-result/notification.json \
  --provider teams
```

User mentions require explicit provider identity arguments. Teams group
mentions remain visible as a configuration notice because Workflow webhooks
cannot mention a group directly. Automation rendering has no default hero
image, so a live CI send cannot accidentally reference the committed synthetic
asset host.

Operational jobs can add `--teams-compact` when facts already carry the body
meaning, and `--teams-hide-group-mention-notice` when the responsible group is
represented outside Teams. The GitLab jobs use both options so cards avoid
duplicating the fallback body and do not present a setup warning as if it were
an actionable mention.

The integrated AKS example uses this CLI from GitLab. GitHub approval and Argo
CD synchronization submit canonical JSON through GitLab's trigger webhook,
while the scheduled maintenance job invokes the typed scenario arguments.

All names, IDs, routes, timestamps, and URLs are synthetic.
