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

The configuration is deliberately a demonstration control plane, not a
production event bus. If event volume or delivery guarantees grow beyond these
four scenarios, replace pipeline dispatch with a private queue-backed service
without changing the canonical notification contract.
