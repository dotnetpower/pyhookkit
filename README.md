# PyHookKit

Typed Slack and Microsoft Teams notification delivery with semantic parity,
followed by a controlled migration path.

## Slack and Teams parity

PyHookKit preserves the notification's meaning while allowing each provider to
use its native presentation model. One canonical notification is rendered into
different payload shapes; visual identity is not treated as parity.

| Concern | Slack | Microsoft Teams |
|---|---|---|
| Card model | Incoming Webhook attachment with Block Kit blocks | Workflow message with an Adaptive Card 1.4 attachment |
| Severity | Colored attachment rail | Centered semantic label and color |
| Facts | Two-column `mrkdwn` fields | Styled `ColumnSet` fact panel |
| User mention | Adapter-resolved `<@USER_ID>` | Adapter-resolved `<at>` text plus mention entity |
| Group mention | Native `<!subteam^GROUP_ID>` | Visible group fallback with an explicit Workflow capability warning |
| Link action | Block Kit URL button | `Action.OpenUrl` |
| Reply and lifecycle | `thread_ts`, `chat.update`, and `chat.delete` where supported | No one-to-one Teams Workflow equivalent in the paired examples |
| Delivery | Incoming Webhook or Slack Web API | Teams Workflow callback URL or routed Azure Logic App |

### Example coverage

| Example | Slack | Microsoft Teams |
|---|---|---|
| [F00 Raw HTTP request](examples/python/fundamentals/00_http_request) | Standard-library webhook POST | Standard-library Workflow POST |
| [F01 Hello World](examples/python/fundamentals/01_hello_world) | Minimal text payload | Minimal Adaptive Card |
| [F02 Basic notification](examples/python/fundamentals/02_basic_notification) | Title, body, severity, and timestamp | Not yet added |
| [F03 Rich card](examples/python/fundamentals/03_rich_card) | Block Kit facts and context | Adaptive Card fact panel and context |
| [F04 Mention](examples/python/fundamentals/04_mention) | User and user-group aliases | Not yet added |
| [F05 Link and action](examples/python/fundamentals/05_link_and_action) | Block Kit URL button | Not yet added |
| [F06 Image](examples/python/fundamentals/06_image) | External image block with alt text | Adaptive Card image with alt text |
| [F07 Routing](examples/python/fundamentals/07_routing) | Logical route resolved to a webhook | Not yet added |
| [F08 Thread or reply](examples/python/fundamentals/08_thread_or_reply) | Known parent `thread_ts` | Not yet added |
| [F09 Update and delete](examples/python/fundamentals/09_update_and_delete) | Web API mutation payloads | Not yet added |
| [F10 Error and retry](examples/python/fundamentals/10_error_and_retry) | Redacted result and bounded retry | Not yet added |
| [Deployment result](examples/python/scenarios/deployment_result) | Paired Block Kit scenario | Paired Adaptive Card scenario |
| [Incident alert and acknowledgment](examples/python/scenarios/incident_alert_acknowledgment) | Native user-group mention and two links | Explicit group fallback and two `Action.OpenUrl` actions |
| [Approval request](examples/python/scenarios/approval_request) | Native user mention and review link | Native user mention entity and review action |
| [Maintenance notice](examples/python/scenarios/maintenance_notice) | Native user-group mention and status link | Explicit group fallback and status action |

## Scenario screenshots

No client screenshots are currently committed. The PNG files under
`examples/python/teams_adaptive_cards/assets/` are card content, not client
captures. Add only actual Slack or Teams client captures under
[`docs/assets/card-previews/`](docs/assets/card-previews/README.md); do not use
synthetic HTML or renderer previews to fill this gallery.

| Scenario | Slack | Microsoft Teams |
|---|---|---|
| [Deployment result](examples/python/scenarios/deployment_result) | _Screenshot pending: `deployment-result-slack.png`_ | _Screenshot pending: `deployment-result-teams.png`_ |
| [Incident alert and acknowledgment](examples/python/scenarios/incident_alert_acknowledgment) | _Screenshot pending: `incident-alert-acknowledgment-slack.png`_ | _Screenshot pending: `incident-alert-acknowledgment-teams.png`_ |
| [Approval request](examples/python/scenarios/approval_request) | _Screenshot pending: `approval-request-slack.png`_ | _Screenshot pending: `approval-request-teams.png`_ |
| [Maintenance notice](examples/python/scenarios/maintenance_notice) | _Screenshot pending: `maintenance-notice-slack.png`_ | _Screenshot pending: `maintenance-notice-teams.png`_ |

## Repository layout

- `contracts/`: language-neutral schemas and paired test vectors
- `docs/`: public usage, architecture, security, and migration guidance
- `examples/python/`: Python 3.12 reference implementation and examples
- `infra/`: provider configuration, runtime infrastructure, integrations, and
  policy checks

Examples are organized by capability or scenario. Where parity is complete,
Slack and Teams entrypoints are siblings and consume the same canonical
notification.

## Local configuration

Copy `.env.example` to the ignored `.env`, then add the Slack Incoming Webhook
URL and Teams Workflow callback URL for synthetic test destinations. See
[Provider configuration](docs/configuration.md) for the exact values and setup
steps and [Slack examples](docs/slack-examples.md) for the F01-F10 catalog.

## Status

The Python distribution and import namespace are both `pyhookkit`. The project
has not been published to PyPI yet.

Paired scenario renderers are complete for Slack and Teams. Fundamental-level
Teams parity is still being added incrementally, as shown in the coverage table.
All committed values are synthetic; runtime credentials and real destination
configuration belong outside this repository.

Third-party example assets and their licenses are listed in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).