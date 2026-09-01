# Slack infrastructure

Slack infrastructure currently consists of the synthetic
[`app-manifest/`](app-manifest/README.md) used by provider-specific operational
examples.

Workspace installation, OAuth consent, signing secrets, bot tokens, app-level
tokens, and destination channel IDs remain runtime configuration. The manifest
declares capabilities but never contains issued credentials.

For local values and scope guidance, see
[`../../docs/configuration.md`](../../docs/configuration.md). For executable
operations, see
[`../../examples/python/slack_operations/README.md`](../../examples/python/slack_operations/README.md).
