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
