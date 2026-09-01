# Integrated Bookinfo notification scenario

This runbook demonstrates approval, deployment, incident, and maintenance
notifications across GitHub, GitLab, Argo CD, AKS, Power Automate, and Microsoft
Teams.

> **Capture status:** GitHub, GitLab, Argo CD, AKS, Bookinfo, Power Automate run
> history, and the Teams approval card are included. The remaining Teams cards
> are pending a working Teams web capture.

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
    gitlab -->|canonical notification| power[Power Automate]
    power --> teams[Microsoft Teams]
```

Each control plane has one responsibility:

| Component | Responsibility |
|---|---|
| GitHub | Source workflow and protected staging approval |
| GitLab | GitOps validation, promotion, and provider delivery |
| Argo CD | Reconcile `gitops-staging` into AKS |
| AKS | Run the Istio-free Bookinfo workload and incident probe |
| Power Automate | Accept the Adaptive Card envelope and post it to Teams |
| Teams | Present the notification and navigation action |

Provider credentials do not cross these boundaries. GitHub and the AKS probe
use separate GitLab trigger tokens. Argo CD uses a short-lived GitLab project
access token in the `PRIVATE-TOKEN` header. Only GitLab stores
`TEAMS_WORKFLOW_URL`.

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

![Teams deployment approval request](assets/integrated-scenario/teams-approval-request.png)

## Scenario 2: GitOps promotion and deployment result

The GitLab promotion pipeline validates every Kustomize tree before changing
the active Reviews patch. Its CI job token writes only to the protected
`gitops-staging` branch.

![GitLab validation and Bookinfo promotion jobs](assets/integrated-scenario/gitlab-promotion-pipeline.png)

Argo CD detects the commit, runs the PostSync smoke Job, and reports a
successful operation. The notification controller then starts a GitLab
canonical-notification pipeline.

![GitLab pipeline started by Argo CD](assets/integrated-scenario/gitlab-argocd-notification-pipeline.png)

_Teams deployment-result card capture pending._

## Scenario 3: incident alert and acknowledgment

The one-time in-cluster probe requests an intentionally invalid product page
path. Failure is expected: the Job builds a canonical incident, submits it to
GitLab, and exits successfully only after GitLab accepts the request.

GitLab validates the manifests and sends the incident card through the same
provider adapter.

![GitLab incident validation and notification jobs](assets/integrated-scenario/gitlab-incident-pipeline.png)

The acknowledgment action opens the GitLab new-issue page. GitLab Issues, not
Teams, is the acknowledgment system of record.

_Teams incident card capture pending._

## Scenario 4: maintenance notice

A disabled-by-default GitLab schedule supplies
`action=maintenance-notice`. The job derives a bounded staging window and links
the card to the exact pipeline.

![GitLab maintenance notification job](assets/integrated-scenario/gitlab-maintenance-pipeline.png)

The live Teams renderer uses compact presentation: required meaning remains in
the canonical fallback, while the visible card avoids repeating the body and
does not present the unsupported group-expansion notice as an action.

_Teams maintenance card capture pending._

## Power Automate delivery

### Create the flow from blank

Do not use the **Send webhook alerts to a channel** gallery template for this
scenario. Template-origin flows add owner attribution and a **Get template**
footer that cannot be removed from the Adaptive Card payload.

1. Open [Power Automate](https://make.powerautomate.com) and select the target
   environment.
2. Select **Create**, then **Create from blank**.
3. Name the flow using an environment-neutral name such as
   `PyHookKit Teams Flow`.
4. Add the Microsoft Teams trigger **When a Teams webhook request is
   received**.
5. Set **Who can trigger the flow?** to **Anyone** for the signed callback URL
   model used by this example.
6. Add the Microsoft Teams action **Post card in a chat or channel** directly
   after the trigger.

The completed flow has one trigger and one action:

![Power Automate flow with Teams webhook trigger and post-card action](assets/integrated-scenario/power-automate-flow-designer.png)

### Configure the Teams action

Set the action fields as follows:

| Field | Value |
|---|---|
| **Post as** | `Flow bot` |
| **Post in** | `Channel` |
| **Team** | The dedicated synthetic test Team |
| **Channel** | The dedicated notification test channel |
| **Adaptive Card** | `triggerBody()?['attachments'][0]['content']` |

![Power Automate Teams post-card action settings](assets/integrated-scenario/power-automate-teams-action.png)

The expression extracts the inner Adaptive Card from PyHookKit's Teams
`message` envelope. Do not paste the full incoming envelope into the Adaptive
Card field.

### Save and distribute the callback safely

1. Select **Save**.
2. Reopen the trigger and copy its generated **HTTP URL**.
3. Treat the complete URL as a credential because its query string contains the
   callback signature.
4. Add it to GitLab under **Settings → CI/CD → Variables** with:
   - key: `TEAMS_WORKFLOW_URL`;
   - visibility: **Masked**;
   - protection: **Protected**;
   - expansion: disabled.
5. Do not store the URL in GitHub, Argo CD, Kubernetes manifests, screenshots,
   terminal transcripts, or repository files.
6. Add a co-owner before using the flow as a shared or long-lived integration.

See the provider-specific [Power Automate Teams Workflow
runbook](../infra/teams-workflows/README.md#attribution-free-flow-created-from-blank)
for footer verification and repeated deployment guidance.

### Smoke test

From `examples/python`, render first:

```shell
uv run python scenarios/deployment_result/teams.py
```

After checking that the payload contains no real secret or identity, load the
ignored local environment and send deliberately:

```shell
set -a
. ../../.env
set +a
uv run python scenarios/deployment_result/teams.py --send
```

The CLI must return `state: succeeded`. Confirm the card in Teams and then
confirm the corresponding Power Automate run is **Succeeded**.

The live flow is enabled and its run history shows the webhook requests used by
the scenarios completing successfully.

![Power Automate flow details and successful run history](assets/integrated-scenario/power-automate-flow-history.png)

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
