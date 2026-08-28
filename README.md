# PyHookKit

Typed Slack and Microsoft Teams notification delivery with semantic parity,
followed by a controlled migration path.

## Repository layout

- `contracts/`: language-neutral schemas and paired test vectors
- `docs/`: public usage, architecture, security, and migration guidance
- `examples/python/`: Python 3.12 reference implementation and examples
- `infra/`: provider configuration, runtime infrastructure, integrations, and
  policy checks

Examples are organized by capability or scenario. Slack and Teams entrypoints
are siblings and consume the same canonical notification.

## Local configuration

Copy `.env.example` to the ignored `.env`, then add the Slack Incoming Webhook
URL and Teams Workflow callback URL for synthetic test destinations. See
[Provider configuration](docs/configuration.md) for the exact values and setup
steps and [Slack examples](docs/slack-examples.md) for the F01-F10 catalog.

## Status

The Python distribution and import namespace are both `pyhookkit`. The project
has not been published to PyPI yet.

The repository is in its Slack reference implementation phase.
All committed values are synthetic; runtime credentials and real destination
configuration belong outside this repository.

Third-party example assets and their licenses are listed in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).