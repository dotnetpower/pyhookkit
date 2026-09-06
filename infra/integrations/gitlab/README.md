# GitLab CI and notification dispatch

GitLab is the single automation boundary between event producers and provider
delivery:

- GitHub submits approval notifications and approved promotion inputs.
- Argo CD submits canonical deployment result JSON.
- The AKS probe submits canonical incident JSON.
- A scheduled pipeline submits maintenance notices.

Only GitLab stores `TEAMS_WORKFLOW_URL` and the selected
`TEAMS_WORKFLOW_CHANNEL_LINK`. Upstream systems receive separate, revocable
pipeline trigger tokens and never receive the Teams credential.

When the `notification-path` pipeline input is `router`, GitLab instead submits
canonical JSON to the central router. In that mode GitLab stores only its
router producer token; provider credentials remain in the router runtime.

## Project model

Import this repository into a dedicated synthetic GitLab project and keep the
Bookinfo GitOps branch under GitLab control. Argo CD reads that branch with a
read-only deploy key. The pipeline validates manifests, updates only the
staging Reviews variant during promotion, and sends provider-neutral
notifications through PyHookKit.

The root `.gitlab-ci.yml` is ready when this repository is imported. Protect the
GitOps branch from direct user pushes while allowing the pipeline service
account to update it.

## Protected variables

Configure these masked and protected values in GitLab:

| Variable | Purpose |
|---|---|
| `TEAMS_WORKFLOW_URL` | Power Automate Workflow callback URL |
| `TEAMS_WORKFLOW_CHANNEL_LINK` | Exact allowlisted Teams channel destination |
| `TEAMS_LOGIC_APP_URL` | Azure Logic App HTTP trigger callback URL |
| `TEAMS_LOGIC_APP_TEAM_ID` | Explicit Teams destination |
| `TEAMS_LOGIC_APP_CHANNEL_ID` | Explicit Teams channel destination |
| `NOTIFICATION_ROUTER_URL` | HTTPS central router base URL |
| `NOTIFICATION_ROUTER_TOKEN` | GitLab-specific central router bearer token |

Configure provider identity variables only when a canonical notification
contains a native user mention. Group mentions remain visible as an explicit
Teams capability notice and do not require Graph permissions.

Enable **Allow Git push requests to the repository using a CI job token** for
the project. The promotion job uses its short-lived `CI_JOB_TOKEN` to update the
protected `gitops-staging` branch, so no long-lived repository write token is
required.

Create separate pipeline trigger tokens for GitHub and the AKS probe. Argo CD
uses a short-lived GitLab project access token in the `PRIVATE-TOKEN` header.
Separate credentials make each producer independently revocable even though
they target the same pipeline.

## Trigger contracts

Canonical notification producers use:

```text
POST /api/v4/projects/<project-id>/trigger/pipeline?token=<token>&ref=main
variables[CANONICAL_NOTIFICATION]=<canonical JSON>
```

Set the project's minimum role allowed to use pipeline variables to
**Maintainer**. Each trigger token is owned by a Maintainer, so canonical input
is accepted while lower-role callers cannot override pipeline variables.
Promotion requests use the same trigger API with the typed `action` and
`reviews-version` pipeline inputs:

```text
POST /api/v4/projects/<project-id>/trigger/pipeline?token=<token>&ref=main
```

Never pass credentials as pipeline inputs or ordinary trigger variables.

Create a GitLab pipeline schedule with `action=maintenance-notice` to exercise
the maintenance scenario. The job derives a one-hour synthetic staging window,
links to the exact GitLab pipeline, and sends a compact Teams card through the
same provider-neutral scenario CLI. The canonical group owner remains in the
fallback text while the live card suppresses the Graph configuration banner;
GitLab remains the operational ownership system of record.

The `teams-delivery` pipeline input accepts `workflow` (default) or
`logic-app`. The Logic App option requires all three `TEAMS_LOGIC_APP_*`
variables.

The `notification-path` input accepts `direct` (default) or `router`. Direct
preserves the existing Teams delivery path. Router sends the canonical input
before provider rendering and requires the two `NOTIFICATION_ROUTER_*`
variables. Keep the paths mutually exclusive for an event to prevent duplicate
messages.

## Router network placement

GitLab project Webhooks send GitLab-specific payloads and do not match the
router's canonical contract. Use the existing CI job to transform and submit
notifications instead of pointing a raw project Webhook at
`/v1/notifications`.

- For a publicly reachable router, set `NOTIFICATION_ROUTER_URL` to the HTTPS
	API-gateway address and keep `NOTIFICATION_ROUTER_TOKEN` masked and protected.
	Expose only the notification API, not the administration dashboard.
- For a private router, run the notification job on a self-hosted GitLab Runner
	that can reach the router over the private network. The Runner initiates its
	GitLab connection outbound, so the router needs no public ingress.
- If a private Runner is unavailable, place a signature-verifying public edge
	and durable queue in front of a private worker. A queue adapter is not
	included in this repository.
- If only direct Teams delivery is required, use `notification-path=direct` and
	the existing shared Power Automate flow. Do not create another flow merely to
	relay traffic to the private router.

See the [central router network guidance](../../../docs/central-notification-router.md#connect-github-and-gitlab-to-the-router)
for topology and security details.

Set optional `NOTIFICATION_ROUTER_TARGET_ID` when router mode must address one
destination instead of every target on the canonical route.

For a Project Webhook, use GitLab's **Generate signing token** option and store
the one-time `whsec_` value in the router secret store. The inbound receiver
validates Standard Webhooks HMAC-SHA256 headers and timestamp freshness. Do not
use the legacy plaintext `X-Gitlab-Token` for new integrations. See the
[producer integrations guide](../../../docs/producer-integrations.md#gitlab-project-webhook).

The configuration is deliberately a demonstration control plane, not a
production event bus. If event volume or delivery guarantees grow beyond these
four scenarios, replace pipeline dispatch with a private queue-backed service
without changing the canonical notification contract.
