# Azure infrastructure

Azure assets support the optional runtime and routed Teams delivery paths:

- [`bicep/`](bicep/README.md) provisions the minimal AKS baseline;
- [`logic-apps/`](logic-apps/README.md) documents routed Teams delivery through
  an authorized managed connector;
- [`parameters/`](parameters/README.md) defines the committed parameter
  boundary.

The Power Automate Teams Workflow is not an Azure deployment artifact. Its
manual setup is documented in
[`../../docs/power-automate-teams-workflow.md`](../../docs/power-automate-teams-workflow.md).

Subscription IDs, tenant IDs, connection authorization, signed callback URLs,
deployment outputs, and state must remain outside this directory.
