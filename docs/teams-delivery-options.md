# Teams delivery options

Teams Workflows is the initial parity target. Logic Apps, Microsoft Graph with
resource-specific consent, or a Teams bot are advanced adapters for behavior
that a Workflow webhook cannot provide.

The selected adapter must expose its supported capabilities and ownership
requirements.

## Azure Logic App delivery

Logic App delivery is not an endpoint-only substitution. The two HTTP contracts
are different:

| Surface | Power Automate Workflow | Azure Logic App `post-card` |
|---|---|---|
| Request body | Teams `message` envelope with `teamId`, `channelId`, and one Adaptive Card attachment | `teamId`, `channelId`, optional `eventId`, and inner `card` |
| Routing | Router-stored channel link resolved to explicit IDs | Explicit Team and Channel IDs per request |
| Endpoint success | Workflow 2xx status | `post-card` returns `201` with Teams message identifiers |
| Authentication | Signed Workflow callback URL | Signed Logic App trigger URL plus authorized Teams API connection |

PyHookKit keeps one `TeamsMessageRenderer` and adapts only the delivery boundary.
Use `--send-logic-app`; do not place a Logic App URL in `TEAMS_WORKFLOW_URL`.
The adapter validates and redacts the callback URL, extracts exactly one
Adaptive Card attachment, adds configured routing, and returns the same redacted
provider-neutral delivery result used by Workflow delivery. Both adapters treat
any 2xx response as success. They intentionally discard the provider response
body and message identifiers rather than leaking provider payloads into the
result contract.

Both adapters retry rate limits, transient `5xx` responses, and transport
failures up to three attempts. `Retry-After` takes precedence on `429`;
otherwise bounded exponential backoff with jitter is used. Validation,
authentication, permission, and other permanent failures are not retried.

```shell
uv run python scenarios/deployment_result/teams.py --send-logic-app
```

See the [Logic App runbook](../infra/azure/logic-apps/README.md) for the trigger
schema and infrastructure assets. See the
[Logic App Teams delivery guide](logic-app-teams-delivery.md) for deployment,
selection, live testing, and removal.

Contract tests execute every library-backed Teams example through both adapters
and assert that the resolved inner Adaptive Card is unchanged. The raw F00
example has the equivalent assertion for its standard-library request builders.

## Workflow lifecycle

The initial routed Workflow is created manually because selecting a Microsoft
connection and granting consent are environment-specific operations. One
callback accepts routed card bodies, so a separate Flow is not required for
each notification channel.

For repeated deployments, package the flow in a Power Platform Solution and
deploy it through Power Platform CLI with a connection reference. Treat
connection authorization and ownership as explicit bootstrap
requirements, and write the generated callback URL directly to a secret store.

After the initial from-blank flow is exported, later environments can be
provisioned without opening the Power Automate portal:

1. pack and import the Solution with Power Platform CLI;
2. bind the Teams connection reference;
3. activate the flow;
4. retrieve the trigger URL through `listCallbackUrl`;
5. place it directly into the environment's secret store;
6. run the footer and rich-card smoke test.

Power Platform CLI deploys Solution artifacts but does not provide a
step-by-step flow designer. Direct creation through Dataverse workflow JSON is
an advanced, version-sensitive alternative and is not the recommended
bootstrap path.

See the [Power Automate Teams Workflow guide](power-automate-teams-workflow.md)
for manual creation and smoke testing, and the
[Teams Workflows runbook](../infra/teams-workflows/README.md) for deployment
automation and ownership.

## Rendering and attribution

`TeamsMessageRenderer` produces Adaptive Card 1.4 payloads with severity
styling, headings, facts, images, source context, links, and user mention
entities. Teams Workflow cannot mention a distribution list directly. Group
notification is an advanced configuration: resolve members through Microsoft
Graph, then render each member as an individual mention. This requires
application credentials, administrator consent for `GroupMember.Read.All`, and
explicit handling for membership and the 28 KB card-size limit. Until that
adapter is configured, the group alias remains visible with a
configuration-required notice.
Thread targeting and message mutation are also unavailable through Workflow
webhooks. F08 renders a visible new-message fallback with its requested thread
key, while F09 renders an explicit unsupported notice. True replies, updates,
and deletion require a bot or Microsoft Graph adapter with persisted Teams
message identifiers and suitable permissions.

The visual hierarchy uses:

- a full-bleed Microsoft editorial sample image;
- a centered severity label and title without emoji;
- the PyHookKit route as subtle centered context;
- responsive two-column fact tiles;
- a bright mention panel;
- an image with accessible alt text and caption;
- compact source and timestamp text;
- clearly labeled `Action.OpenUrl` buttons.

Image URLs must be publicly reachable over HTTPS for Teams to render them.
Committed payloads use synthetic markers. Live sends resolve those markers from
`EXAMPLE_ASSET_BASE_URL`, with `TEAMS_ASSET_BASE_URL` retained as a compatible
fallback.

See [Teams Adaptive Card design](teams-adaptive-cards.md) for the official
best-practice baseline and standalone example gallery.

Live testing established:

| Delivery flow | Rich card | Native user mention | `Get template` |
|---|---:|---:|---:|
| Teams Workflow gallery template | Yes | Yes | Shown |
| Power Automate flow built from blank | Yes | Yes | Not shown |

The gallery footer is generated by Teams, not by the notification payload.
Payload changes cannot remove it. A from-blank flow currently avoids the
footer; use a Teams bot or suitable Graph adapter when sender identity and
attribution must be contractually controlled.

Power Automate exposes the causal distinction on the flow details page:
template-created flows have an **Original template** relationship, while the
verified from-blank flow does not. The footer's **Get template** link targets
that original template. Deployment verification should therefore check both
the details page and an actual posted card rather than relying on the flow name
or copied action definitions.

This footer is the Teams Workflow template discoverability feature tracked by
[Microsoft 365 Roadmap 393923](https://www.microsoft.com/microsoft-365/roadmap?featureid=393923).
It applies to template-origin flows and is outside the incoming webhook payload.
Renaming, cloning with uncertain metadata, or changing Adaptive Card elements
is not a reliable removal strategy.
