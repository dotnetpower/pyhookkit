# Provider configuration

The repository uses one local environment file for provider destination
credentials:

```shell
cp .env.example .env
```

Keep each URL inside double quotes because signed URLs can contain shell
characters such as `&`. The committed `.env.example` is the variable contract;
the ignored `.env` is the only local file that may contain real values.

## Slack

Set:

```dotenv
SLACK_WEBHOOK_URL="<Slack Incoming Webhook URL>"
```

You need:

1. A Slack workspace where an administrator permits app installation.
2. A synthetic test channel.
3. A Slack app with **Incoming Webhooks** enabled.
4. The app installed or reinstalled in the workspace and authorized for the
   test channel.
5. The Incoming Webhook URL issued for that channel.

Create the app in the current Slack UI:

1. Open the [Slack app management page](https://api.slack.com/apps) and select
   **Create an app**.
2. In **Create new app**, select **Blank app** under
   **Or start your own way**, then select **Continue**.
3. Enter a synthetic name such as `PyHookKit Sandbox`, choose the
   development workspace, and create the app.
4. In the app settings sidebar, select **Incoming Webhooks**.
5. Turn **Activate Incoming Webhooks** on.
6. Select **Add New Webhook to Workspace**, choose the synthetic test channel,
   and approve the installation.
7. Under **Webhook URLs for Your Workspace**, copy the generated URL.

Older Slack instructions may call **Blank app** **From scratch**. They refer to
the same minimal app creation path. Do not select **AI agent** or **Starter
app** for this example.

Copy the complete issued URL into `SLACK_WEBHOOK_URL`. An Incoming Webhook is
bound to the selected workspace and destination. A channel name or Slack
channel ID is therefore not required in this initial environment contract.

### Advanced Slack examples

F08 can render a threaded webhook message when a parent message timestamp is
already known. F09 demonstrates Web API update and delete payloads. Live Web
API delivery additionally requires:

```dotenv
SLACK_BOT_TOKEN="<Bot User OAuth Token>"
SLACK_APP_TOKEN="<Socket Mode app-level token>"
SLACK_SIGNING_SECRET="<Slack app signing secret>"
SLACK_CHANNEL_ID="<Slack channel ID>"
SLACK_TEST_DISPLAY_NAME="<test member display name>"
SLACK_USER_ID="<test Slack member ID>"
SLACK_USER_GROUP_ID="<test Slack user-group ID>"
```

- Find the bot token under **OAuth & Permissions → OAuth Tokens for Your
  Workspace** after installing or reinstalling the app. It normally begins
  with `xoxb-`. Treat it as a secret.
- Add only the scopes needed by the operation being tested. The complete
  synthetic manifest includes `chat:write`, `channels:read`, `groups:read`,
  `users:read`, `usergroups:read`, `files:write`, `reactions:write`, and
  `app_mentions:read`. Event examples additionally use `reactions:read`,
  `channels:history`, and `groups:history`.
- Obtain a channel ID from the channel details UI. The channel ID is
  environment configuration, not a secret, but it must not enter the canonical
  notification contract.
- Retain the message `ts` returned by `chat.postMessage` to address a thread,
  update, or delete operation. An Incoming Webhook success body does not return
  this identifier.
- F04 requires a test member ID and test user-group ID only when `--send` is
  used. Rendering uses synthetic identifiers.
- O02 can discover the test member from `SLACK_TEST_DISPLAY_NAME` without
  requesting email access. A display name must resolve to exactly one active,
  non-bot member.
- HTTP interactions and Events API examples require the signing secret. Never
  use the deprecated verification token in its place.
- Socket Mode requires an app-level token with `connections:write`. Its value
  normally begins with `xapp-`; the bot token is still used for Web API writes.

F08-F09 render synthetic payloads and do not make Web API requests. The
`slack_operations` examples provide the live Web API lifecycle.

Create and manage Incoming Webhooks using the
[Slack Incoming Webhooks documentation](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks).

## Microsoft Teams

Set:

```dotenv
TEAMS_WORKFLOW_URL="<Teams Workflow HTTP POST callback URL>"
TEAMS_WORKFLOW_CHANNEL_LINK="<exact approved Microsoft Teams channel link>"
TEAMS_LOGIC_APP_URL="<Azure Logic App HTTP trigger callback URL>"
TEAMS_LOGIC_APP_TEAM_ID="<Microsoft Teams team ID>"
TEAMS_LOGIC_APP_CHANNEL_ID="<Microsoft Teams channel ID>"
EXAMPLE_ASSET_BASE_URL="<direct HTTPS base URL for committed example images>"
TEAMS_ASSET_BASE_URL="<legacy fallback; leave blank for new configuration>"
TEAMS_TEST_USER_ID="<test member Microsoft Entra object ID or UPN>"
TEAMS_TEST_USER_NAME="<test member display name>"
```

You need:

1. A Microsoft 365 account that can create Workflows in Teams.
2. A synthetic test team and channel.
3. One Power Automate flow created from blank with the HTTP request trigger,
  routed request schema, exact channel-link allowlist, link parsing, and
  dynamic post action.
4. An authorized Teams connection owned by a dedicated licensed Microsoft 365
  user that is a member of the destination Team.
5. A Dataverse application user for service-principal ownership in shared or
  production environments, plus at least two named operational co-owners.
6. The HTTP POST callback URL generated after the Workflow is saved.

Copy the complete generated callback URL into `TEAMS_WORKFLOW_URL`, and copy an
exact allowlisted Teams channel link into `TEAMS_WORKFLOW_CHANNEL_LINK`. The
callback is shared by all approved destinations; the link selects the Team and
Channel for each request. Do not accept arbitrary links merely because the
connection user can access them.

For Azure Logic App delivery, configure the signed HTTP trigger URL separately
from the explicit Team and channel IDs. Follow the
[Logic App Teams delivery guide](logic-app-teams-delivery.md); a Logic App
callback cannot replace `TEAMS_WORKFLOW_URL` because its request schema is
different.

The provider-neutral asset base is used by image-led paired scenarios and
standalone Adaptive Card examples for both Workflow and Logic App delivery.
`TEAMS_ASSET_BASE_URL` is read only as a compatible fallback when
`EXAMPLE_ASSET_BASE_URL` is blank. The two `TEAMS_TEST_*` values are optional
and used only by the standalone mention example. Do not set these example
values in shared production notification configuration.

Create and smoke-test the from-blank flow with the
[Power Automate Teams Workflow guide](power-automate-teams-workflow.md).
The Solution deployment, service-principal ownership, and channel-access tools
are in the
[Teams Workflows runbook](../infra/teams-workflows/README.md).

For repeated environments, deploy the verified flow as a Power Platform
Solution with Power Platform CLI and retrieve each environment's callback URL
through the management API. Do not copy one environment's signed URL into
another environment or store it in the Solution source.

## Loading the file

From the repository root, load the values into the current shell:

```shell
set -a
. ./.env
set +a
```

Check that a value exists without printing the credential:

```shell
test -n "$SLACK_WEBHOOK_URL" && echo "Slack destination configured"
test -n "$TEAMS_WORKFLOW_URL" && echo "Teams destination configured"
test -n "$TEAMS_WORKFLOW_CHANNEL_LINK" && echo "Teams channel route configured"
test -n "$TEAMS_LOGIC_APP_URL" && echo "Teams Logic App configured"
```

Fundamental examples render payloads by default. Slack operations are also
dry-run by default and require an explicit `--live`, `--send`, `--exercise`,
`--upload`, `--serve`, or `--listen-once` flag before network activity.
Entrypoints read variables at the composition boundary; domain and application
code never read `.env` directly.

## Security and rotation

- Treat both URLs as credentials even when they target test channels.
- Never paste either value into source, tests, fixtures, screenshots, logs,
  command history, issues, or pull requests.
- Do not print environment values during debugging or CI.
- If a URL is exposed, revoke or replace the Slack webhook or regenerate the
  Teams Workflow callback URL, then update the approved secret store.
- Production deployments must inject the same variables from a secret manager
  rather than copying `.env`.
- Add bot tokens, OAuth credentials, tenant IDs, or client credentials only
  when a concrete advanced adapter requires them.
