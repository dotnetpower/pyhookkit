# PyHookKit

[한국어](README.ko.md)

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
| Group mention | Native `<!subteam^GROUP_ID>` | Additional Graph member-expansion configuration required |
| Link action | Block Kit URL button | `Action.OpenUrl` |
| Reply and lifecycle | `thread_ts`, `chat.update`, and `chat.delete` where supported | Explicit Workflow fallback/unsupported cards; bot or Graph required for mutation |
| Delivery | Incoming Webhook or Slack Web API | Teams Workflow callback URL or routed Azure Logic App |

### Recommended Teams delivery

The Teams examples are implemented against a Power Automate Workflow created
from blank. The flow receives the Adaptive Card envelope through **When a Teams
webhook request is received** and posts its card content to the configured
channel with **Post card in a chat or channel**.

This is the recommended default for channel notifications. The central router
stores approved channel links and their derived metadata, then sends an
Adaptive Card message envelope with `teamId` and `channelId` through one shared
Flow callback.
Live testing confirmed rich cards and native user mentions without the owner attribution and
**Get template** footer added by gallery-template Workflows. A gallery template
remains useful for a quick proof of concept, while Azure Logic Apps are better
suited to Azure-managed deployments or callers that already own direct Team and
Channel IDs.
Features such as true replies, updates, deletion, or controlled sender identity
require a Teams bot or Microsoft Graph adapter.

Follow the [Power Automate Teams Workflow setup
guide](docs/power-automate-teams-workflow.md) for the verified trigger, action,
Adaptive Card expression, credential handling, screenshots, and smoke-test
steps. Use the [Azure Logic App Teams delivery
guide](docs/logic-app-teams-delivery.md) when per-request Team and channel
routing is required. See [Teams delivery
options](docs/teams-delivery-options.md) for the tested alternatives and their
trade-offs.

### Integrated delivery scenario

The infrastructure example runs Istio-free Bookinfo on AKS and connects all
three delivery control planes without duplicating their responsibilities:
GitHub provides the staging approval, GitLab validates and promotes the GitOps
revision, and Argo CD reconciles it to AKS. Approval, deployment, incident, and
maintenance events retain the provider-neutral contract until a GitLab job
renders and sends them through Power Automate.

See the [infrastructure guide](docs/infrastructure.md#aks-bookinfo-notification-environment)
for the architecture and bootstrap order.

The [integrated Bookinfo scenario](docs/integrated-bookinfo-scenario.md)
includes the live approval, GitOps promotion, Argo CD reconciliation, incident,
maintenance, and Teams delivery evidence.

### Optional central router

GitLab and Argo CD can submit the same canonical contract to a small
SQLite-backed central router. It provides producer authentication,
route-to-many-destination fan-out, per-target status, and idempotent acceptance
while reusing the existing Slack and Teams adapters. Direct delivery remains an
explicit migration and fallback path.

See the [central notification router guide](docs/central-notification-router.md)
for route configuration, local execution, and producer integration. Use the
[TeamsNotifyApp bootstrap guide](docs/teams-notify-app-bootstrap.md) for visible
app registration, minimum operator roles, automatic environment setup, and
membership diagnostics.

## End-to-end Teams setup

This walkthrough starts in one target Microsoft Entra tenant and finishes with
one canonical notification delivered through the SQLite central router, Power
Automate, and Microsoft Teams. Commands run from the repository root unless a
step says otherwise.

### Distinguish the tenants and users first

In this walkthrough, **Azure tenant**, **Microsoft Entra tenant**, and
**Microsoft 365 tenant** do not mean separate user directories. The Microsoft
Entra tenant is the identity directory. Microsoft 365 and Teams provide
licensed services to users from that directory. A "Microsoft 365 user" is
therefore a user in the **same Entra tenant with Microsoft 365/Teams licenses**,
not a separate type of account.

The Power Platform environment also belongs to the target Entra tenant. This
PyHookKit walkthrough keeps all of the following in the **same Entra tenant
identified by the channel link**:

- the destination Team and channel;
- the Power Platform environment and Power Automate Flow;
- the `svc-teams-notification` Teams connection user;
- the `TeamsNotifyApp` app registration and Service Principal.

An Azure subscription is an Azure resource and billing boundary, separate from
the Entra tenant. This Power Automate path uses Azure CLI only for Entra ID and
Microsoft Graph calls, so **no Azure subscription or Azure RBAC role is
required**. Azure subscription Contributor or Owner does not grant any of the
Entra, Power Platform, or Teams permissions in this walkthrough. A subscription
is required only when deploying the optional [Azure Logic App Teams
delivery](docs/logic-app-teams-delivery.md).

### Prerequisites

| Requirement | Purpose |
|---|---|
| Python 3.12 and `uv` | Install and run PyHookKit |
| Azure CLI | Create and verify `TeamsNotifyApp` in the target Entra tenant, not an Azure subscription |
| Microsoft 365 tenant with Teams | Own destination Teams, channels, and all user identities |
| Power Platform environment in the same tenant | Own the Power Automate Flow and Teams connection |
| Dedicated licensed user such as `svc-teams-notification` | Authorize the Teams connector and post notifications |
| Teams channel link | Derive tenant, Team, channel, and display-name metadata |

### Identity and minimum-permission matrix

One person can perform more than one role, but permissions do not transfer
between roles. For example, an Azure subscription Owner cannot create the Flow,
and a Flow author cannot post a card when the Teams connection user is not a
member of the destination Team.

| Identity or actor | Account boundary | Minimum permission or license | Steps |
|---|---|---|---|
| Local operator | Developer or operator; need not be a tenant account | Repository and local `.env` access | 1, 4, 8-10 |
| User and license provisioner | Administrator in the target Entra tenant | **User Administrator** can create the account and assign its licenses. For license-only work on an existing account, use **License Administrator** or the organization's existing provisioning process | 2 |
| Team owner or existing member | User in the target Microsoft 365 tenant | Initial channel access and permission to obtain its link; Team owner when manually adding members | 2 |
| Flow author | Person with access to the Power Platform environment in the target Entra tenant | **Environment Maker** in the target environment and any Power Automate entitlement required by tenant policy | 3 |
| Teams connection user | Ordinary user in the same Entra tenant, such as `svc-teams-notification` | Microsoft 365/Teams and Power Automate entitlements, membership in every destination Team, and ability to complete interactive OAuth/MFA; no Entra administrator role | 2, 3, 7 |
| Flow operational co-owner | Named person with access to the target Power Platform environment | Co-owner access to the Flow; cannot manage another user's Teams connection credential | 3, 7 |
| Bootstrap app creator | Person signed in to the target Entra tenant | No directory role if user app registration is allowed; otherwise **Application Developer**; owner of the created `TeamsNotifyApp` | 5, 6 |
| Consent approver | Administrator in the target Entra tenant | **Privileged Role Administrator** to grant admin consent for Microsoft Graph application permission `GroupMember.ReadWrite.All`; activate temporarily through PIM when available | 5, 6 |
| `TeamsNotifyApp` | Non-human app registration and Service Principal in the target tenant | Admin-consented Graph application permission `GroupMember.ReadWrite.All`; no Microsoft 365 license, Azure RBAC, or Power Platform role | 6, 8, 9 |
| Notification producer and central router | Local process or CI/CD workload | Producer uses a router bearer token; router uses the signed Workflow callback secret; neither must be a Microsoft 365 user or Entra administrator | 8-10 |

To create the app registration and grant admin consent in one
`bootstrap-teams-app` invocation, the signed-in bootstrap identity must have
**both the app-creator and consent-approver permissions**. To separate duties,
have the app creator create the app, have the consent approver complete admin
consent, and then rerun the command to verify it.

The **Dataverse application user** used for repeat Solution deployment is not
`TeamsNotifyApp`. The former owns and deploys the Flow; the latter manages Team
membership through Graph. The first manually authored end-to-end setup does not
require a Dataverse application user.

### Step 1: Install the project

**Actor:** local operator. No Microsoft cloud permission is required.

```shell
cp .env.example .env
chmod 600 .env

cd examples/python
uv sync --extra dev --python 3.12
cd ../..
```

The ignored `.env` contains local credentials. Never commit, print, paste, or
attach it to an issue.

### Step 2: Prepare the Teams connection user and channel

**Actors:** user/license provisioner and Team owner. After provisioning,
`svc-teams-notification` operates as an ordinary user with no administrator
role.

1. Create or designate the dedicated `svc-teams-notification` user.
2. Assign the Microsoft 365/Teams and Power Automate entitlements required by
   the tenant.
3. Keep the account as an ordinary user; do not assign an Entra administrator
   role.
4. In Teams, open the initial standard channel, select **More options** >
   **Get link to channel**, and retain the complete
   `https://teams.cloud.microsoft/l/channel/...` link.

The link contains the tenant ID, Team backing-group ID, channel ID, and channel
name. PyHookKit validates and stores those values separately in SQLite.

### Step 3: Create and configure the Power Automate Flow

**Actor:** Flow author. The Teams connection sign-in and MFA in item 7 are
completed as `svc-teams-notification`. These accounts do not need to be the
same.

1. Open [Power Automate](https://make.powerautomate.com) and select the target
   environment.
2. Select **Create** and create an automated cloud Flow from blank.
3. Use an environment-neutral name such as `PyHookKit Routed Teams Flow`.
4. Add **When a Teams webhook request is received**.
5. Set **Who can trigger the flow?** to **Anyone** for the signed callback model.
6. Add **Post card in a chat or channel** directly after the trigger.
7. Under **Change connection**, sign in as `svc-teams-notification`. The account
   shown under **Connected to** is the identity whose Team access is enforced.
8. Configure the action:

   | Field | Value |
   |---|---|
   | **Post as** | `Flow bot` |
   | **Post in** | `Channel` |
   | **Team** | Custom expression `triggerBody()?['teamId']` |
   | **Channel** | Custom expression `triggerBody()?['channelId']` |
   | **Adaptive Card** | Expression `first(triggerBody()?['attachments'])?['content']` |

9. Save the Flow.
10. Reopen the trigger and copy its complete **HTTP URL**, including all query
    parameters and the signature.
11. Add at least two named Flow co-owners for recovery. Co-ownership does not
    change the Teams connection identity.

Do not use `triggerBody()` as the Adaptive Card value. The trigger body is a
Teams message envelope; only the first attachment's `content` is the card.

### Step 4: Store the Workflow callback

**Actor:** local operator with write access to the callback secret store.

Add the complete callback to the repository root `.env`:

```dotenv
TEAMS_WORKFLOW_URL="<complete signed Power Automate HTTP URL>"
```

Treat this URL as a credential. The central router SQLite database stores only
the environment variable name, never the callback value.

### Step 5: Choose how to create TeamsNotifyApp

**Actors:** bootstrap app creator and consent approver. Azure Portal is used
only as an Entra administration UI; no Azure subscription role is involved.

Choose one of these paths:

- **Path A — create it directly in the portal:** Use this path to review the
  app registration, permission, and owners in the UI. Then run the command in
  step 6 to configure the credential, Team membership, and first route.
- **Path B — create everything with one command:** Use this path to automate
  the app registration through first-route configuration. Then skip step 6 and
  verify the result in step 7.

#### Path A: Create it directly in Azure Portal

For explicit portal review and ownership, create the app as follows:

1. Open **Microsoft Entra ID** > **App registrations** > **New registration**.
2. Set the name to `TeamsNotifyApp`.
3. Select **Accounts in this organizational directory only**.
4. Leave the redirect URI empty and select **Register**.
5. Open **API permissions** > **Add a permission** > **Microsoft Graph** >
   **Application permissions**.
6. Search for and select `GroupMember.ReadWrite.All`.
7. Select **Add permissions**.
8. A user with **Privileged Role Administrator** selects **Grant admin consent
   for \<tenant\>** and confirms.
9. Under **Owners**, add at least two named operational owners.

Do not add `Group.ReadWrite.All`; it is broader than the required membership
permission. Do not manually create a client secret unless an external secret
manager owns it. The bootstrap command creates, validates, and protects the
local example credential.

#### Path B: Create everything with one command

This path requires all of the following:

- the signed `TEAMS_WORKFLOW_URL` from step 4 in the repository-root `.env`;
- the initial Teams channel link and the `svc-teams-notification` user name;
- a signed-in identity with app-registration permission and an active
  **Privileged Role Administrator** role.

Run from the repository root. An Azure subscription is not required:

```shell
az login \
  --tenant "<tenant ID from the channel link>" \
  --use-device-code \
  --allow-no-subscriptions

cd examples/python
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  bootstrap-teams-app \
  --channel-link "<initial Teams channel link>" \
  --connection-user "svc-teams-notification@example.com" \
  --route release-notifications
cd ../..
```

The command creates `TeamsNotifyApp` and its Service Principal, configures the
`GroupMember.ReadWrite.All` application permission, and persists admin consent.
It also creates and validates the client credential, adds the connection user
to the Team, and registers the first destination route in SQLite. It never
prints the generated secret and writes it to `.env` with mode `0600`.

The command writes `TEAMS_NOTIFY_TENANT_ID`, `TEAMS_NOTIFY_CLIENT_ID`,
`TEAMS_NOTIFY_CLIENT_SECRET`, and `TEAMS_CONNECTION_USER_ID` to `.env`.

> [!IMPORTANT]
> This command does not replace interactive OAuth or MFA for the user-owned
> Power Automate Teams connection, and it does not add operational co-owners.
> Authorize the Teams connection in step 3 and add or verify at least two named
> operational owners in step 7.

### Step 6: Bootstrap the Path A app and first route

**Actor:** bootstrap identity holding both the app-creator and consent-approver
permissions. An Azure subscription is not required:

Run this step only if you selected **Path A** in step 5. If you selected
**Path B**, the same work is already complete; continue to step 7.

```shell
az login \
  --tenant "<tenant ID from the channel link>" \
  --use-device-code \
  --allow-no-subscriptions
```

Run from `examples/python`:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  bootstrap-teams-app \
  --channel-link "<initial Teams channel link>" \
  --connection-user "svc-teams-notification@example.com" \
  --route release-notifications
```

The command creates or reuses `TeamsNotifyApp` and its Service Principal,
verifies the Graph app-role assignment, creates and validates a client
credential, resolves the connection user's object ID, writes generated values
to `.env` with mode `0600`, adds the user to the Team when absent, and stores
the route in SQLite. Secrets are never printed.

Generated values are:

```dotenv
TEAMS_NOTIFY_TENANT_ID="<tenant GUID>"
TEAMS_NOTIFY_CLIENT_ID="<TeamsNotifyApp client GUID>"
TEAMS_NOTIFY_CLIENT_SECRET="<generated secret>"
TEAMS_CONNECTION_USER_ID="<connection user object GUID>"
```

### Step 7: Verify Azure Portal and Power Automate

**Actors:** `TeamsNotifyApp` owner and Flow operational co-owner. They can be
different people.

In **App registrations** > `TeamsNotifyApp`:

- confirm **API permissions** contains Microsoft Graph
  `GroupMember.ReadWrite.All` as an **Application** permission;
- confirm its status is **Granted for \<tenant\>**;
- confirm only expected credentials and owners exist; add named operational
  owners in this step when fewer than two are present.

In **Enterprise applications** > `TeamsNotifyApp`:

- confirm the Service Principal is visible;
- confirm the same granted application permission.

In Power Automate:

- confirm the Flow is enabled;
- confirm the Teams action is **Connected to** `svc-teams-notification`;
- confirm the Team, Channel, and Adaptive Card expressions exactly match step 3.

### Step 8: Add another channel

**Actor:** central-router operator. It uses the `TeamsNotifyApp` credential and
callback secret from `.env`, not a person's Azure or Microsoft 365 permissions.

The command loads `.env`, obtains a new app-only Graph token, ensures Team
membership, and stores the channel metadata:

```shell
cd examples/python

uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id teams-example-channel \
  --route release-notifications \
  --provider teams-workflow \
  --endpoint-env TEAMS_WORKFLOW_URL \
  --channel-link "<another Teams channel link>" \
  --ensure-team-membership
```

Repeat with a unique target ID for every channel. Destinations using the same
route receive the same notification independently.

### Step 9: Run diagnostics

**Actor:** central-router operator.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  doctor
```

Expected healthy output:

```json
{
  "state": "healthy",
  "workflowUrl": "valid",
  "graphAppToken": "valid",
  "teamsDestinations": 2,
  "memberships": "verified",
  "databaseMode": "0600"
}
```

`doctor` validates the callback format, app-only token, token tenant/client and
role, all enabled Team memberships, and SQLite permissions. It does not send a
notification.

### Step 10: Send an end-to-end test

**Actors:** local notification producer and central-router operator. Neither
process signs in as a Microsoft 365 user.

Terminal 1, from `examples/python`:

```shell
export PYHOOKKIT_LOCAL_ROUTER_TOKEN="$(
  python -c 'import secrets; print(secrets.token_urlsafe(32))'
)"

uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  serve \
  --producer local=PYHOOKKIT_LOCAL_ROUTER_TOKEN
```

Terminal 2, using the same generated token:

```shell
cd examples/python
export NOTIFICATION_ROUTER_URL="http://127.0.0.1:8080"
export NOTIFICATION_ROUTER_TOKEN="<same local router token>"

uv run python -m pyhookkit.entrypoints.notification_router_client \
  --producer local \
  --input ../../contracts/test-vectors/scenarios/deployment-result/notification.json
```

The submit command returns `202`-style `queued` state and a notification ID.
Query its final state:

```shell
curl --fail --silent \
  -H "X-PyHookKit-Producer: local" \
  -H "Authorization: Bearer $NOTIFICATION_ROUTER_TOKEN" \
  "$NOTIFICATION_ROUTER_URL/v1/notifications/<notification ID>"
```

Confirm `delivered` and one `succeeded` item per destination. In Power Automate,
confirm one successful run per destination, and in Teams confirm that the card
appears once in every configured channel.

For secret rotation, failure recovery, and removal, use the detailed
[TeamsNotifyApp bootstrap guide](docs/teams-notify-app-bootstrap.md).

### Example coverage

| Example | Slack | Microsoft Teams |
|---|---|---|
| [F00 Raw HTTP request](examples/python/fundamentals/00_http_request) | Standard-library webhook POST | Standard-library Workflow POST |
| [F01 Hello World](examples/python/fundamentals/01_hello_world) | Minimal text payload | Minimal Adaptive Card |
| [F02 Basic notification](examples/python/fundamentals/02_basic_notification) | Title, body, severity, and timestamp | Adaptive Card title, body, severity, and timestamp |
| [F03 Rich card](examples/python/fundamentals/03_rich_card) | Block Kit facts and context | Adaptive Card fact panel and context |
| [F04 Mention](examples/python/fundamentals/04_mention) | Native user and user-group mentions | Native user mention; group expansion requires Graph configuration |
| [F05 Link and action](examples/python/fundamentals/05_link_and_action) | Block Kit URL button | `Action.OpenUrl` |
| [F06 Image](examples/python/fundamentals/06_image) | External image block with alt text | Adaptive Card image with alt text |
| [F07 Routing](examples/python/fundamentals/07_routing) | Logical route resolved to a webhook | Logical route resolved to a Workflow |
| [F08 Thread or reply](examples/python/fundamentals/08_thread_or_reply) | Known parent `thread_ts` | Explicit new-message fallback; bot or Graph required for replies |
| [F09 Update and delete](examples/python/fundamentals/09_update_and_delete) | Web API mutation payloads | Explicit unsupported notice; bot or Graph required |
| [F10 Error and retry](examples/python/fundamentals/10_error_and_retry) | Redacted result and bounded retry | Redacted result and bounded retry |
| [Deployment result](examples/python/scenarios/deployment_result) | Paired Block Kit scenario | Paired Adaptive Card scenario |
| [Incident alert and acknowledgment](examples/python/scenarios/incident_alert_acknowledgment) | Native user-group mention and two links | Group configuration notice and two `Action.OpenUrl` actions |
| [Approval request](examples/python/scenarios/approval_request) | Native user mention and review link | Native user mention entity and review action |
| [Maintenance notice](examples/python/scenarios/maintenance_notice) | Native user-group mention and status link | Group configuration notice and status action |

## Client screenshots

The PNG files under `examples/python/teams_adaptive_cards/assets/` are card
content, not client captures. Add only actual Slack or Teams client captures
under [`docs/assets/card-previews/`](docs/assets/card-previews/README.md); do not
use synthetic HTML or renderer previews to fill this gallery.

| Example | Slack | Microsoft Teams |
|---|---|---|
| [F01 Hello World](examples/python/fundamentals/01_hello_world) | <img src="./docs/assets/card-previews/hello-world-slack.png" alt="Hello World notification in Slack"> | <img src="./docs/assets/card-previews/hello-world-teams.png" alt="Hello World notification in Microsoft Teams"> |
| [F02 Basic notification](examples/python/fundamentals/02_basic_notification) | <img src="./docs/assets/card-previews/basic-notification-slack.png" alt="Basic notification in Slack"> | <img src="./docs/assets/card-previews/basic-notification-teams.png" alt="Basic notification in Microsoft Teams"> |
| [F03 Rich card](examples/python/fundamentals/03_rich_card) | <img src="./docs/assets/card-previews/rich-card-slack.png" alt="Rich card notification in Slack"> | <img src="./docs/assets/card-previews/rich-card-teams.png" alt="Rich card notification in Microsoft Teams"> |
| [F04 Mention](examples/python/fundamentals/04_mention) | <img src="./docs/assets/card-previews/mention-slack.png" alt="Mention notification in Slack"> | <img src="./docs/assets/card-previews/mention-teams.png" alt="Mention notification in Microsoft Teams"><ul><li><sub>Group notification requires additional Microsoft Graph member-expansion configuration.</sub></li><li><sub>Teams displays the configured user name because substituting a logical alias can misidentify the mentioned person.</sub></li></ul> |
| [F05 Link and action](examples/python/fundamentals/05_link_and_action) | <img src="./docs/assets/card-previews/link-and-action-slack.png" alt="Link and action notification in Slack"> | <img src="./docs/assets/card-previews/link-and-action-teams.png" alt="Link and action notification in Microsoft Teams"> |
| [F06 Image](examples/python/fundamentals/06_image) | <img src="./docs/assets/card-previews/image-slack.png" alt="Image notification in Slack"> | <img src="./docs/assets/card-previews/image-teams.png" alt="Image notification in Microsoft Teams"> |
| [F07 Routing](examples/python/fundamentals/07_routing) | <img src="./docs/assets/card-previews/route-slack.png" alt="Routed notification in Slack"> | <img src="./docs/assets/card-previews/route-teams.png" alt="Routed notification in Microsoft Teams"> |
| [Deployment result](examples/python/scenarios/deployment_result) | _Screenshot pending: `deployment-result-slack.png`_ | <img src="./docs/assets/card-previews/deployment-result-teams.png" alt="Bookinfo deployment result in Microsoft Teams"> |
| [Incident alert and acknowledgment](examples/python/scenarios/incident_alert_acknowledgment) | _Screenshot pending: `incident-alert-acknowledgment-slack.png`_ | <img src="./docs/assets/card-previews/incident-alert-acknowledgment-teams.png" alt="Bookinfo incident alert in Microsoft Teams"> |
| [Approval request](examples/python/scenarios/approval_request) | _Screenshot pending: `approval-request-slack.png`_ | <img src="./docs/assets/card-previews/approval-request-teams.png" alt="Bookinfo deployment approval request in Microsoft Teams"> |
| [Maintenance notice](examples/python/scenarios/maintenance_notice) | _Screenshot pending: `maintenance-notice-slack.png`_ | <img src="./docs/assets/card-previews/maintenance-notice-teams.png" alt="Scheduled maintenance notice in Microsoft Teams"> |

## Repository layout

- [`contracts/`](contracts/README.md): language-neutral schemas and paired test
  vectors
- [`docs/`](docs/README.md): public usage, architecture, security, and
  migration guidance
- [`examples/`](examples/README.md): reference implementations and examples
- [`infra/`](infra/README.md): provider configuration, runtime infrastructure,
  integrations, and policy checks

Examples are organized by capability or scenario. Where parity is complete,
Slack and Teams entrypoints are siblings and consume the same canonical
notification.

Every user-facing documentation, infrastructure, test, and executable-example
directory has a README entrypoint. Source-package directories, frozen fixture
leaf directories, generated caches, and nested image-only asset directories are
documented by their nearest parent README instead of duplicating local files.

## Local configuration

Copy `.env.example` to the ignored `.env`, then add the Slack Incoming Webhook
URL and Teams Workflow callback URL for synthetic test destinations. See
[Provider configuration](docs/configuration.md) for the exact values and setup
steps and [Slack examples](docs/slack-examples.md) for the F01-F10 catalog.

## Status

The Python distribution and import namespace are both `pyhookkit`. The project
has not been published to PyPI yet.

Paired fundamental and scenario examples are complete for Slack and Teams.
Provider differences are explicit when Teams Workflow lacks an equivalent
operation. All committed values are synthetic; runtime credentials and real
destination configuration belong outside this repository.

Third-party example assets and their licenses are listed in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).