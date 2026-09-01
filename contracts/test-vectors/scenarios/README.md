# Scenario test vectors

Each directory contains one provider-neutral `notification.json` plus frozen
`slack.expected.json` and `teams.expected.json` renderings.

| Vector | Semantics preserved by both snapshots |
|---|---|
| [`deployment-result`](deployment-result/) | result, severity, service, environment, revision, duration, timestamp, details link |
| [`incident-alert-acknowledgment`](incident-alert-acknowledgment/) | alert, severity, incident, service, start, acknowledgment state, responder alias, acknowledgment and runbook links |
| [`approval-request`](approval-request/) | request, severity, subject, requester, deadline, approver alias, review link |
| [`maintenance-notice`](maintenance-notice/) | notice, severity, window, affected services, expected impact, owner alias, status-page link |

Slack snapshots use structured Block Kit facts, native mapped mentions, and
link buttons. Teams snapshots freeze an image-led editorial header, semantic
severity labels, responsive fact columns, source context, user mention entities,
image treatment, and `Action.OpenUrl` buttons. Teams Workflow group notification
remains an explicit degradation. Required meaning and navigation URLs also
remain in fallback text. Parity is semantic rather than payload-shape equality.

Every fixture uses synthetic values and validates against
`contracts/notification.schema.json`.
