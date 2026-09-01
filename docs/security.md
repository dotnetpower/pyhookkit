# Security

Only synthetic payloads, aliases, identifiers, routes, and URLs may be
committed. Webhook URLs and tokens are credentials.

Do not log raw notifications or provider responses that may disclose sensitive
data. Inject runtime secrets by reference from an approved secret manager.

`.env` is ignored and intended only for local development.
`.env.example` defines variable names with blank values and must never contain
credentials. Treat webhook URLs, `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`,
`SLACK_SIGNING_SECRET`, and the Teams Workflow URL as credentials.

## Credential ownership

| Credential | Approved owner |
|---|---|
| Slack webhook and API tokens | Local `.env` or deployment secret store |
| Power Automate and Logic App callback URLs | GitLab protected masked variables |
| GitLab producer trigger token | Calling control plane's secret store |
| Argo CD GitLab project token | `argocd-notifications-secret` |
| Kubernetes administrator credentials | Operator kubeconfig outside Git |

Use a distinct revocable token for each producer. GitHub and the AKS incident
probe must not share the Argo CD project token. Give the Argo token the shortest
practical expiration and send it in the `PRIVATE-TOKEN` header, never in a URL
or notification body.

## Logging and evidence

- Never log raw canonical notifications when they can contain user-provided
  facts, URLs, or identities.
- Delivery results contain provider-neutral state, attempt count, and redacted
  error classification only.
- Do not log callback URLs, provider response bodies, Socket Mode URLs, or
  request headers containing credentials.
- Crop screenshots to the smallest useful area and remove accounts, tenants,
  subscriptions, Teams destinations, connection identities, and signed URLs.
- Strip image metadata before committing captures.
- Rotate any credential visible in a log, screenshot, shell history, or issue.

Inbound Slack HTTP requests must be verified against the exact raw body,
`X-Slack-Request-Timestamp`, and `X-Slack-Signature`. Requests older than five
minutes are rejected to limit replay attacks. Socket Mode URLs returned by
Slack are short-lived credentials and must not be logged.

See [Provider configuration](configuration.md) for local setup and rotation
guidance and the [Power Automate Teams Workflow
guide](power-automate-teams-workflow.md) for callback storage.
