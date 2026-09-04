# Notification parity

[한국어](notification-parity.ko.md)

Parity means preserving the event, outcome, required facts, mentions, links,
and core user action. Provider payloads are not expected to have identical JSON
or visual layout.

Unsupported or degraded behavior must be reported explicitly rather than
silently omitted.

## Canonical boundary

`contracts/notification.schema.json` is the provider-neutral input. Domain
objects and fixtures may contain logical routes and identity aliases, but never
provider payload fields, destination URLs, Slack IDs, Teams IDs, or SDK types.

| Meaning | Canonical field |
|---|---|
| Event identity | `eventId` |
| Logical destination | `route` |
| Outcome | `severity`, `title`, `body` |
| Structured context | ordered `facts` |
| Navigation | labeled HTTPS `links` |
| Notification targets | logical `mentions` |
| Correlation | `threadKey`, `metadata.correlationId` |
| Source context | `sourceTimestamp`, `metadata.source` |

## Capability classification

Every requested behavior is classified before provider rendering:

- **equivalent**: both providers preserve the behavior natively;
- **degraded**: required meaning remains, but interaction or presentation
  differs;
- **advanced adapter**: the basic webhook cannot provide the behavior, while an
  authenticated adapter can;
- **unsupported**: no configured adapter can preserve the request.

Examples:

| Capability | Slack | Teams Workflow |
|---|---|---|
| Severity, facts, URL action | Equivalent | Equivalent |
| User mention | Native mapped ID | Native mapped mention entity |
| Group mention | Native user group | Degraded notice or Graph expansion |
| Thread reply | Known `thread_ts` | Advanced bot or Graph adapter |
| Update and delete | Slack Web API | Advanced bot or Graph adapter |

## Verification

Each fundamental or scenario has:

1. one canonical `notification.json`;
2. a frozen Slack expected payload;
3. a frozen Teams expected payload;
4. schema validation;
5. semantic assertions for required facts, links, mentions, and actions;
6. negative tests for rejected or unsupported inputs.

Snapshot equality is provider-specific. Parity tests compare required meaning,
not JSON shape or pixels. Live tests remain necessary for client rendering,
external image retrieval, native mentions, buttons, and provider-generated
attribution.

See [`contracts/test-vectors/`](../contracts/test-vectors/README.md) for the
fixture catalogs and [`examples/python/scenarios/`](../examples/python/scenarios/README.md)
for complete notification examples.
