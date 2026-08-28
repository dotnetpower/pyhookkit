# Security

Only synthetic payloads, aliases, identifiers, routes, and URLs may be
committed. Webhook URLs and tokens are credentials.

Do not log raw notifications or provider responses that may disclose sensitive
data. Inject runtime secrets by reference from an approved secret manager.

`.env` is ignored and intended only for local development.
`.env.example` defines variable names with blank values and must never contain
credentials. Treat webhook URLs, `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`,
`SLACK_SIGNING_SECRET`, and the Teams Workflow URL as credentials.

Inbound Slack HTTP requests must be verified against the exact raw body,
`X-Slack-Request-Timestamp`, and `X-Slack-Signature`. Requests older than five
minutes are rejected to limit replay attacks. Socket Mode URLs returned by
Slack are short-lived credentials and must not be logged.

See [Provider configuration](configuration.md) for local setup and rotation
guidance.
