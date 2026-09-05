# Microsoft Teams Webhook notification guide

[한국어](README.ko.md)

Send an Adaptive Card to a standard Microsoft Teams channel with one HTTP
request, much like a Slack Incoming Webhook. The first notification requires no
router and no Microsoft Graph application.

## Fastest path

Follow the [10-minute Teams Webhook quickstart](teams-webhook-quickstart.md) to
complete three tasks:

1. **Add a posting identity to the Team.** The Power Automate Teams action runs
  with the signed-in connection user, so that identity needs a Teams license
  and Team membership.
2. **Create one shared Power Automate flow.** The flow reads the Team, channel,
  and Adaptive Card from each request and serves every standard channel.
3. **Send a standard-library test.** Set only the channel link and flow callback
  URL. The test does not run the `pyhookkit` package or a server.

> [!NOTE]
> The 10-minute path assumes Power Automate access, an existing licensed posting
> identity, and a standard channel. For production, prefer a dedicated ordinary
> user such as `svc-teams-notification` over an employee identity.

## Why each component exists

| Component | Why it exists | Required? |
|---|---|---|
| Microsoft 365 posting identity | The Teams connector posts with this user's permissions and Team access. | Yes. An existing licensed user works for a quick test. |
| Shared Power Automate flow | Creates the signed HTTP URL and maps each request's destination and Adaptive Card to the Teams action. | Yes |
| `TeamsNotifyApp` Graph app | Adds the posting identity to the backing Microsoft 365 Groups for many Teams. | Optional. A Team owner can add the identity manually for the first delivery. |
| PyHookKit router | Moves existing Slack producers behind a controlled route or fans out to Slack and Teams destinations. | Optional |

`TeamsNotifyApp` does not post messages and does not replace the delegated Power
Automate connection. Keep manual membership and avoid Graph application
permission when only a few Teams are involved.

## Guides by task

| Goal | Guide |
|---|---|
| Send the first Teams notification in 10 minutes | [Teams Webhook quickstart](teams-webhook-quickstart.md) |
| Create the shared flow with screenshots | [Power Automate Teams Workflow](power-automate-teams-workflow.md) |
| Design Adaptive Cards | [Teams Adaptive Card design](teams-adaptive-cards.md) |
| Compare Teams delivery methods | [Teams delivery options](teams-delivery-options.md) |
| Protect callbacks and credentials | [Security](security.md) |
| Automate posting-identity membership across many Teams | [TeamsNotifyApp bootstrap](teams-notify-app-bootstrap.md) |
| Run the optional fan-out router | [Central notification router](central-notification-router.md) |
| Understand Slack and Teams semantic parity | [Notification parity](notification-parity.md) |

## Advanced operations and examples

- [Provider configuration](configuration.md)
- [Slack examples](slack-examples.md)
- [Azure Logic App Teams delivery](logic-app-teams-delivery.md)
- [Infrastructure](infrastructure.md)
- [Integrated Bookinfo scenario](integrated-bookinfo-scenario.md)
- [Migration](migration.md)

All committed guidance uses synthetic names, IDs, URLs, routes, and
destinations. Do not add screens or command output containing credentials,
callback signatures, account identities, or real environment identifiers.
