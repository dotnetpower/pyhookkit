# GitLab CI and notification dispatch

GitLab is the single automation boundary between event producers and provider
delivery:

- GitHub submits approval notifications and approved promotion inputs.
- Argo CD submits canonical deployment result JSON.
- The AKS probe submits canonical incident JSON.
- A scheduled pipeline submits maintenance notices.

Only GitLab stores `TEAMS_WORKFLOW_URL`. Upstream systems receive separate,
revocable pipeline trigger tokens and never receive the Teams credential.

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
Configure provider identity variables only when a canonical notification
contains a native user mention. Group mentions remain visible as an explicit
Teams capability notice and do not require Graph permissions.

Enable **Allow Git push requests to the repository using a CI job token** for
the project. The promotion job uses its short-lived `CI_JOB_TOKEN` to update the
protected `gitops-staging` branch, so no long-lived repository write token is
required.

Create separate pipeline trigger tokens for GitHub, Argo CD, and the AKS probe.
Separate tokens make each producer independently revocable even though they
target the same pipeline.

## Trigger contracts

Canonical notification webhooks use:

```text
POST /api/v4/projects/<project-id>/ref/main/trigger/pipeline?token=<token>
Content-Type: application/json
```

GitLab exposes that JSON body to the job as the file-type `TRIGGER_PAYLOAD`
variable. Promotion requests use the trigger API form with the typed `action`
and `reviews-version` pipeline inputs:

```text
POST /api/v4/projects/<project-id>/trigger/pipeline?token=<token>&ref=main
```

Never pass credentials as pipeline inputs or ordinary trigger variables.

Create a GitLab pipeline schedule with `action=maintenance-notice` to exercise
the maintenance scenario. The job derives a one-hour synthetic staging window,
links back to the configured `source-url`, and sends through the same
provider-neutral scenario CLI.

The configuration is deliberately a demonstration control plane, not a
production event bus. If event volume or delivery guarantees grow beyond these
four scenarios, replace pipeline dispatch with a private queue-backed service
without changing the canonical notification contract.
