# Infrastructure

Infrastructure assets are independent of implementation language. Declarative
configuration belongs under `infra`; OAuth consent, generated credentials, and
other imperative steps belong in explicit bootstrap runbooks.

Credentials, callback URLs, state, and real environment parameters must not be
committed.

Teams Workflow infrastructure follows a one-time-authoring and repeated-ALM
model. The verified from-blank flow should be placed in a Power Platform
Solution, deployed with Power Platform CLI, and configured with connection
references and environment variables. Its generated callback URL is recovered
after activation and written directly to a secret store.

See the [Teams Workflows runbook](../infra/teams-workflows/README.md) for the
headless deployment roadmap and template-footer verification checklist.

## AKS Bookinfo notification environment

The integrated example uses Bookinfo as a small, multi-service workload without
installing Istio. GitHub owns deployment approval, GitLab owns CI and
notification dispatch, and Argo CD owns AKS reconciliation. This keeps provider
credentials out of GitHub, Argo CD templates, and the Bookinfo namespace:
`TEAMS_WORKFLOW_URL` exists only as a protected GitLab variable.

Canonical JSON crosses the platform boundaries. GitHub, Argo CD, and the
in-cluster probe do not build Slack or Teams payloads. A GitLab job validates
the canonical input and invokes the same PyHookKit renderers used by the paired
examples.

Bootstrap in this order:

1. provision the minimal [AKS cluster](../infra/azure/bicep/README.md);
2. create the GitLab project from the
   [Bookinfo GitOps assets](../infra/gitops/bookinfo/README.md);
3. configure the [GitLab pipeline](../infra/integrations/gitlab/README.md);
4. install and configure [Argo CD](../infra/integrations/argocd/README.md);
5. add the protected [GitHub approval workflow](../infra/integrations/github/README.md);
6. configure the from-blank
   [Power Automate Teams Workflow](power-automate-teams-workflow.md).

The first iteration intentionally uses an internal health probe rather than a
full Prometheus stack. Argo CD, Istio, managed monitoring, Key Vault CSI, and a
private event service can be introduced independently when their capabilities
are actually needed.
