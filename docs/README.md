# Documentation

This directory contains user-facing architecture, setup, operation, and
migration guidance. Provider or infrastructure implementation details remain
beside the assets they configure under `infra/`.

## Start here

| Goal | Document |
|---|---|
| Run the first paired example | [Getting started](getting-started.md) |
| Configure local provider values | [Provider configuration](configuration.md) |
| Run the SQLite central router | [Central notification router](central-notification-router.md) |
| Understand semantic equivalence | [Notification parity](notification-parity.md) |
| Configure Teams identities and create the delivery flow | [Power Automate Teams Workflow](power-automate-teams-workflow.md) |
| Deploy routed Teams delivery | [Azure Logic App Teams delivery](logic-app-teams-delivery.md) |
| Run the full AKS scenario | [Integrated Bookinfo scenario](integrated-bookinfo-scenario.md) |
| Understand infrastructure boundaries | [Infrastructure](infrastructure.md) |
| Compare Teams delivery adapters | [Teams delivery options](teams-delivery-options.md) |
| Design Teams cards | [Teams Adaptive Cards](teams-adaptive-cards.md) |
| Explore Slack capabilities | [Slack examples](slack-examples.md) |
| Review credential boundaries | [Security](security.md) |
| Plan provider migration | [Migration](migration.md) |

## Documentation boundaries

- `docs/` explains what a user chooses and how to operate it.
- `infra/**/README.md` explains how a concrete infrastructure asset is
  provisioned, connected, validated, and removed.
- `examples/python/**/README.md` explains one executable example or catalog.
- `contracts/**/README.md` explains language-neutral schemas and fixtures.

All committed instructions use synthetic names, IDs, URLs, routes, and
destinations. Never add screenshots or command output containing credentials,
callback signatures, account identities, or real environment identifiers.
