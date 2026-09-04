# Integrated Bookinfo notification scenario

[한국어](integrated-bookinfo-scenario.ko.md)

This runbook demonstrates approval, deployment, incident, and maintenance
notifications across GitHub, GitLab, Argo CD, AKS, Power Automate, and Microsoft
Teams.

> **Capture status:** GitHub, GitLab, Argo CD, AKS, Bookinfo, and all four Teams
> scenario cards are included. Power Automate setup and runtime evidence is kept
> in the separate [Power Automate Teams Workflow guide](power-automate-teams-workflow.md).

## Architecture

```mermaid
flowchart LR
    developer[Developer] --> github[GitHub Actions]
    github -->|approval request| gitlab[GitLab pipeline]
    github -->|approved promotion| gitlab
    gitlab -->|GitOps commit| argocd[Argo CD]
    argocd -->|sync| aks[AKS Bookinfo]
    argocd -->|deployment result| gitlab
    aks -->|incident probe| gitlab
    gitlab -->|canonical notification| delivery{Teams delivery}
    delivery -->|workflow| power[Power Automate]
    delivery -->|routed| logic[Azure Logic App]
    power --> teams[Microsoft Teams]
    logic --> teams
```

Each control plane has one responsibility:

| Component | Responsibility |
|---|---|
| GitHub | Source workflow and protected staging approval |
| GitLab | GitOps validation, promotion, and provider delivery |
| Argo CD | Reconcile `gitops-staging` into AKS |
| AKS | Run the Istio-free Bookinfo workload and incident probe |
| Power Automate | Post router-supplied Adaptive Cards to explicit Teams IDs |
| Azure Logic App | Optional direct Team and Channel ID routing |
| Teams | Present the notification and navigation action |

Provider credentials do not cross these boundaries. GitHub and the AKS probe
use separate GitLab trigger tokens. Argo CD uses a short-lived GitLab project
access token in the `PRIVATE-TOKEN` header. Only GitLab stores the Teams
Workflow and Logic App callback credentials.

## Live environment

The reference environment uses one OIDC-enabled AKS node and intentionally
omits Istio, ingress, ACR, and a monitoring stack.

![AKS resources returned by Azure Portal search](assets/integrated-scenario/azure-aks-resources.png)

Bookinfo runs in `bookinfo-staging`. The product page verifies that
`productpage`, `details`, `ratings`, and `reviews` communicate inside the
cluster.

![Bookinfo product page on AKS](assets/integrated-scenario/bookinfo-productpage.png)

Argo CD reports the application as both `Healthy` and `Synced`, and its tree
shows the provider-neutral Kubernetes resources.

![Argo CD Bookinfo application tree](assets/integrated-scenario/argocd-bookinfo-application.png)

## Scenario 1: deployment approval

1. An operator dispatches `bookinfo-release.yml` with Reviews v1, v2, or v3.
2. GitHub builds a canonical approval request.
3. GitLab validates it and sends the Teams approval card.
4. The `bookinfo-staging` GitHub Environment pauses promotion.
5. A required reviewer approves or rejects the deployment in GitHub.
6. Approval starts the GitLab promotion pipeline.

The Teams button opens the GitHub run; it does not approve the deployment
directly.

![GitHub deployment waiting for environment approval](assets/integrated-scenario/github-approval-pending.png)

After approval, both the request and promotion jobs complete.

![GitHub deployment approval and completed promotion](assets/integrated-scenario/github-approval-complete.png)

The compact approval card preserves the selected application and Reviews
version, requester, GitHub environment reviewer boundary, deadline, and review
action without repeating the canonical fallback body.

![Teams deployment approval request](assets/card-previews/approval-request-teams.png)

## Scenario 2: GitOps promotion and deployment result

The GitLab promotion pipeline validates every Kustomize tree before changing
the active Reviews patch. Its CI job token writes only to the protected
`gitops-staging` branch.

![GitLab validation and Bookinfo promotion jobs](assets/integrated-scenario/gitlab-promotion-pipeline.png)

Argo CD detects the commit, runs the PostSync smoke Job, and reports a
successful operation. The notification controller then starts a GitLab
canonical-notification pipeline.

![GitLab pipeline started by Argo CD](assets/integrated-scenario/gitlab-argocd-notification-pipeline.png)

![Teams Bookinfo deployment result](assets/card-previews/deployment-result-teams.png)

## Scenario 3: incident alert and acknowledgment

The one-time in-cluster probe requests an intentionally invalid product page
path. Failure is expected: the Job builds a canonical incident, submits it to
GitLab, and exits successfully only after GitLab accepts the request.

GitLab validates the manifests and sends the incident card through the same
provider adapter.

![GitLab incident validation and notification jobs](assets/integrated-scenario/gitlab-incident-pipeline.png)

The acknowledgment action opens the GitLab new-issue page. GitLab Issues, not
Teams, is the acknowledgment system of record.

![Teams Bookinfo incident alert and acknowledgment actions](assets/card-previews/incident-alert-acknowledgment-teams.png)

## Scenario 4: maintenance notice

A disabled-by-default GitLab schedule supplies
`action=maintenance-notice`. The job derives a bounded staging window and links
the card to the exact pipeline.

![GitLab maintenance notification job](assets/integrated-scenario/gitlab-maintenance-pipeline.png)

The live Teams renderer uses compact presentation: required meaning remains in
the canonical fallback, while the visible card avoids repeating the body and
does not present the unsupported group-expansion notice as an action.

![Teams scheduled maintenance notice](assets/card-previews/maintenance-notice-teams.png)

## Teams delivery dependency

All four scenarios select one final Teams delivery adapter. Power Automate
Workflow is the default and reuses one callback across exact allowlisted Teams
destinations stored by the central router. Azure Logic App is optional when
callers already own direct Team and Channel IDs or require Azure-managed
deployment.

Complete the [Power Automate Teams Workflow
guide](power-automate-teams-workflow.md) before running any scenario that sends
through the default path. Complete the
[Logic App Teams delivery guide](logic-app-teams-delivery.md) before selecting
`logic-app`. The infrastructure-oriented [Teams Workflows
runbook](../infra/teams-workflows/README.md) covers repeated deployment,
ownership, and footer verification.

## Verification

The live scenario has verified:

- GitHub environment approval followed by GitLab promotion;
- Reviews v1, v2, and v3 rollout, with v3 restored as the final state;
- Argo CD `Synced` and `Healthy` status;
- the Bookinfo PostSync smoke test;
- GitLab maintenance, canonical, Argo deployment, and AKS incident pipelines;
- Power Automate delivery results succeeding in one attempt;
- notification-controller logs containing no GitLab token-shaped URL or header.

Repository validation consists of:

```shell
cd examples/python
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -q
```

Infrastructure validation:

```shell
az bicep build --stdout --file infra/azure/bicep/main.bicep >/dev/null
az bicep lint --file infra/azure/bicep/main.bicep
kubectl kustomize infra/gitops/bookinfo/overlays/staging >/dev/null
kubectl kustomize infra/integrations/argocd >/dev/null
actionlint -shellcheck= .github/workflows/bookinfo-release.yml
```

## Security and operational notes

- Never commit GitLab tokens, Teams callback URLs, kubeconfigs, or generated
  callback URLs.
- Keep the GitLab pipeline-variable override role at Maintainer or higher.
- Give the Argo CD project token the `api` scope, use the shortest practical
  expiration, and rotate it independently of producer trigger tokens.
- Do not place a trigger token in an Argo CD webhook URL or template body.
- The Teams **Workflows** sender label is controlled by Power Automate. Use a
  bot or suitable Microsoft Graph adapter if sender identity must be controlled.
- Teams Workflow cannot directly mention a group, reply to a thread, or mutate
  a previous message.
- The one-node cluster has limited Pod capacity. Dex and the ApplicationSet
  controller are disabled in the reference Argo CD values.

## Stop or remove the environment

Stop compute while retaining configuration:

```shell
az aks stop --resource-group rg-notify --name aks-notify-b05230
```

Restart it:

```shell
az aks start --resource-group rg-notify --name aks-notify-b05230
```

Remove all Azure resources when the scenario is no longer needed:

```shell
az group delete --name rg-notify
```
