# Infrastructure

Infrastructure assets reproduce provider configuration and runtime deployment
without coupling them to a language implementation.

Real environment overlays, generated credentials, and state remain private.

## Layout

- [`azure/`](azure/README.md): AKS Bicep, Logic Apps, and parameters;
- [`gitops/`](gitops/README.md): declarative workload desired state;
- [`integrations/`](integrations/README.md): GitHub, GitLab, and Argo CD;
- [`runtime/`](runtime/README.md): reserved local, container, and Azure
  composition boundaries;
- [`slack/`](slack/README.md): Slack app manifest;
- [`teams-workflows/`](teams-workflows/README.md): Power Platform lifecycle and
  attribution verification;
- [`policy/`](policy/README.md): infrastructure security expectations.

## Integrated Bookinfo scenario

The minimal end-to-end environment assigns one responsibility to each control
plane:

1. GitHub requests a protected staging approval.
2. GitLab validates and promotes the Bookinfo GitOps revision.
3. Argo CD reconciles that revision into one AKS staging namespace.
4. PyHookKit delivers canonical approval, deployment, incident, and maintenance
   notifications through the Power Automate Teams Workflow.

Start with the [AKS Bicep](azure/bicep/README.md) and
[Bookinfo GitOps](gitops/bookinfo/README.md) assets. Then configure
[GitLab](integrations/gitlab/README.md), [Argo CD](integrations/argocd/README.md),
and [GitHub](integrations/github/README.md), in that order. The environment
deliberately omits Istio, ingress, a container registry, and a monitoring stack.
Those components are not required to demonstrate the four notification
scenarios.

Azure Logic App Teams delivery is documented in
[`azure/logic-apps/README.md`](azure/logic-apps/README.md).
