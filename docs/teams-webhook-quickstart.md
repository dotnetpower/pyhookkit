# Send a Microsoft Teams Webhook notification in 10 minutes

[한국어](teams-webhook-quickstart.ko.md)

This guide creates the minimum configuration needed to notify a Microsoft Teams
channel with one HTTP request, similar to a Slack Incoming Webhook. Create a
dedicated service account in the Microsoft 365 admin center, create one shared
Power Automate flow, and use the repository's standard-library script to send
the first Adaptive Card. The first delivery does not require the PyHookKit
router or a Microsoft Graph app.

> [!NOTE]
> The portal input and flow configuration take about 10 minutes. This estimate
> excludes tenant-policy and service-propagation time before a newly created
> Microsoft 365 user and license become active in Teams.

## Result

After setup, notifications follow this path:

```text
HTTP notification request
    → signed Power Automate Webhook URL
    → posting identity's Microsoft Teams connection
    → standard channel in the requested Team
```

Do not create one Power Automate flow per channel. One flow reads the request's
`teamId`, `channelId`, and Adaptive Card and serves multiple standard channels.

After configuration, the **Hello, world!** Adaptive Card appears in the Teams
channel as shown below.

![Configuration result showing the Hello, world! Adaptive Card posted by Workflows in the Teams channel.](assets/power-automate-teams-workflow/hello-world.png)

## Prerequisites

Prepare:

- a flow author with access to the target tenant's Power Platform environment;
- a **User Administrator** or organizational provisioning operator who can
  create a user and assign licenses;
- available Microsoft 365/Teams and Power Automate entitlements;
- a Team owner who can add that identity as a member;
- the complete **Get link to channel** URL for a standard channel;
- local Python 3.

This guide creates a dedicated ordinary user such as
`svc-teams-notification` so employee departure, password changes, or connection
deletion do not unexpectedly stop the production flow. Do not assign that user
an Entra administrator role.

## Step 1: Create the Microsoft 365 service account—about 2 minutes of portal work

**Actors:** user/licensing provisioning operator and Team owner.

1. Sign in to the [Microsoft 365 admin center](https://admin.cloud.microsoft/).
2. Open **Users** > **Active users** and select **Add a user**.
3. Under **Basics**, enter a synthetic display name and a user name such as
  `svc-teams-notification`, then select the organization's approved domain.
4. Configure the initial credential according to organizational password and
  MFA policy. Never place a real password in documentation, screenshots, Git,
  or issues.
5. Under **Product licenses**, assign entitlements that include Microsoft Teams
  and Power Automate.
6. Create the user and keep it as an ordinary user with no administrator role.
7. A Team owner uses **More options** > **Manage team** on the target Team and
  adds the new service account as a member. This guide targets standard
  channels, which inherit Team membership.

![Enter the Teams notification service account basics in the Microsoft 365 admin center Add a user pane.](assets/power-automate-teams-workflow/create-service-account.png)

### Why a posting identity is required

**Post card in a chat or channel** does not run with an application identity. It
posts with the user signed in to the Power Automate Microsoft Teams connection.
The posting identity therefore needs:

- Teams and Power Automate entitlements;
- membership in every target Team;
- interactive sign-in permission to authorize the connection and complete MFA.

The administrator creating the account needs user-provisioning and licensing
access, but the resulting service account needs no Entra administrator role or
Azure subscription role.

> [!IMPORTANT]
> Private and shared channels do not grant access through Team membership alone.
> Use a standard channel for this 10-minute path.

## Step 2: Create the shared Power Automate flow—about 5 minutes

**Actor:** flow author. Authorize the Microsoft Teams connection as the service
account created in step 1.

1. Open [Power Automate](https://make.powerautomate.com) and select the target
   environment.
2. Create an automated cloud flow from blank.
3. Add **When a Teams webhook request is received**.
4. Set **Who can trigger the flow?** to **Anyone**.
5. Add **Post card in a chat or channel** directly after the trigger.
6. Under **Change connection**, sign in as the posting identity and complete MFA.
7. Configure the action:

   | Field | Value |
   |---|---|
   | **Post as** | `Flow bot` |
   | **Post in** | `Channel` |
   | **Team** | `triggerBody()?['teamId']` |
   | **Channel** | `triggerBody()?['channelId']` |
   | **Adaptive Card** | `first(triggerBody()?['attachments'])?['content']` |

8. Save the flow and copy the trigger's complete **HTTP URL**.

![Shared Power Automate flow with the Teams Webhook request trigger connected to the channel card action.](assets/power-automate-teams-workflow/shared-flow-overview.png)

For every UI selection with screenshots, use the [Power Automate Teams Workflow
detailed guide](power-automate-teams-workflow.md).

### Why a shared flow is required

The Teams Webhook trigger creates a signed HTTP entrypoint but does not directly
post the request to a channel. The Teams action reads the destination and card
content from the request and performs the post. Dynamic destination expressions
let every standard channel reuse this flow.

**Anyone** permits an unauthenticated caller, but the complete URL contains the
invocation signature. Treat it like a password; never commit or log it or place
it in screenshots and issues.

## Step 3: Send the first notification—about 3 minutes

The F00 script uses only the Python standard library. It does not import the
`pyhookkit` package or run a router. It extracts Team and channel identifiers
from the Teams channel link and sends a minimal Adaptive Card envelope to the
shared flow.

Before running the command, a Team owner opens the target Team's **Members** tab
and confirms that `svc-teams-notification` is a member. If the account is absent
from **Members and guests**, select **Add member**, find the account, and add it
as a member. Standard channels inherit Team membership, so do not add the
account separately to every standard channel.

![The Teams Members tab shows zero Members and guests before the service account is added.](assets/power-automate-teams-workflow/team-member.png)

After adding the account, expand **Members and guests** and confirm that
`svc-teams-notification` appears with **Team role** set to **Member**. This state
allows the service account's Teams connection to post to standard channels in
that Team.

![The Teams Members and guests list shows the service account with the Member role.](assets/power-automate-teams-workflow/team-member2.png)

If the posting identity is not a member of the target Team, the Webhook trigger
can accept the request while **Post card in a chat or channel** fails to publish
to the channel. For a private or shared channel, also add the posting identity
to that channel explicitly.

Next, store the link for the channel that will receive the notification.

1. In Teams, locate the target channel under **Teams and channels**, then select
  **...** on the right side of the channel.
2. Select **Copy link**.

  ![Select Copy link from the more-options menu on the right side of the target Teams channel.](assets/power-automate-teams-workflow/channel-copy-link.png)

3. Open the Git-ignored `.env` at the repository root, paste the complete copied
  link into the following variable, and save the file:

  ```dotenv
  TEAMS_WORKFLOW_CHANNEL_LINK="<complete copied Teams channel link>"
  ```

  Never place the real value in `.env.example`. If `.env` does not exist at the
  repository root, first copy `.env.example` to `.env` and set its file mode to
  `0600`.

The F00 script resolves the Team ID from the copied link's `groupId` query
parameter and the channel ID from its `/l/channel/` path. It validates the URL
shape before adding explicit `teamId` and `channelId` fields to the Power
Automate request. You do not need to copy either identifier separately.

Choose one of the following tabs to send the first notification. Run each option
from the repository root.

<!-- starlight-tabs:start -->

### Run the script

```shell
set -a
. ./.env
set +a

cd examples/python/fundamentals/00_http_request
python3 teams.py --send
```

### Python

The following standalone Python source extracts both identifiers from the
channel link and posts directly to the Workflow. Load `.env` into the environment
before running it.

```shell
set -a
. ./.env
set +a
```

```python
import json
import os
import urllib.request
from urllib.parse import parse_qs, unquote, urlsplit

channel_link = urlsplit(os.environ["TEAMS_WORKFLOW_CHANNEL_LINK"])
team_id = parse_qs(channel_link.query)["groupId"][0]
channel_id = unquote(channel_link.path.split("/")[3])

payload = {
    "type": "message",
    "teamId": team_id,
    "channelId": channel_id,
    "attachments": [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None,
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [{"type": "TextBlock", "text": "Hello, world!", "wrap": True}],
            },
        }
    ],
}

request = urllib.request.Request(
    os.environ["TEAMS_WORKFLOW_URL"],
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(request, timeout=10.0) as response:
    print(json.dumps({"state": "succeeded", "statusCode": response.status}, indent=2))
```

### curl

The following shell script extracts the Team and channel IDs from the channel
link and sends the same request with `curl`. It does not run Python.

```shell
set -a
. ./.env
set +a

# To set the environment variables directly, uncomment and edit these two lines.
# TEAMS_WORKFLOW_URL="<complete Power Automate HTTP URL>"
# TEAMS_WORKFLOW_CHANNEL_LINK="<complete channel link copied from Teams>"

team_id="${TEAMS_WORKFLOW_CHANNEL_LINK#*groupId=}"
team_id="${team_id%%&*}"
encoded_channel_id="${TEAMS_WORKFLOW_CHANNEL_LINK#*/l/channel/}"
encoded_channel_id="${encoded_channel_id%%/*}"
printf -v channel_id '%b' "${encoded_channel_id//%/\\x}"

payload="$(cat <<JSON
{
  "type": "message",
  "teamId": "$team_id",
  "channelId": "$channel_id",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "contentUrl": null,
    "content": {
      "\$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.4",
      "body": [{"type": "TextBlock", "text": "Hello, world!", "wrap": true}]
    }
  }]
}
JSON
)"

curl --fail-with-body --silent --show-error \
  --header "Content-Type: application/json" \
  --data "$payload" \
  --output /dev/null \
  --write-out '{"state":"succeeded","statusCode":%{http_code}}\n' \
  "$TEAMS_WORKFLOW_URL"
```

<!-- starlight-tabs:end -->

A successful result resembles:

```json
{
  "state": "succeeded",
  "statusCode": 202
}
```

Confirm a successful Power Automate run and a **Hello, World!** card in the
target Teams channel. The successful `2xx` status can differ by tenant policy or
connector version. The card should resemble the screen shown under **Result**
above.

## Optional: Automate membership with TeamsNotifyApp

The first notification does not require a Microsoft Graph app. A Team owner can
add the posting identity manually.

Register each notification destination separately using its channel link.
Standard channels inherit Team membership, so add `svc-teams-notification` once
per Team rather than once per channel. During channel registration,
`TeamsNotifyApp` checks membership in that Team and uses Microsoft Graph to add
the account only when it is absent.

`TeamsNotifyApp` does not post messages, replace the Power Automate connection
or MFA. For a private channel, it automates both Team and channel membership.
Shared channels are not supported.

> [!NOTE]
> Register `TeamsNotifyApp` to add the Power Automate posting identity,
> `svc-teams-notification`, to notification destinations automatically—not to
> send notifications itself. Standard channels inherit Team membership, so the
> app adds the identity to the Team. Private channels require membership in both
> the Team and channel.
>
> `TeamsNotifyApp` is required when using **Add channel** in the central router
> administration dashboard. The dashboard uses the app's Graph permissions to
> inspect the channel type and configure posting-identity membership. The app
> is not required for router delivery alone when a Team owner manages the
> posting identity manually and an operator registers destinations through the
> CLI.

Automation requires the admin-consented Graph application permission
`Channel.ReadBasic.All`, `ChannelMember.ReadWrite.All`, `TeamMember.Read.All`, and
`TeamMember.ReadWriteNonOwnerRole.All`. Because these permissions are broad, use
the
[TeamsNotifyApp bootstrap guide](teams-notify-app-bootstrap.md) only when you
need to automate membership across several Teams.

## Optional: Use the PyHookKit routing layer

Direct delivery in this quickstart does not require a PyHookKit server. Add the
PyHookKit examples or central router only when you need to:

- redirect an existing notification producer from a Slack Webhook to a
  controlled routing layer;
- fan out one notification to Slack and Teams or multiple Teams channels;
- track per-destination status, idempotent intake, and retry classification;
- render Adaptive Cards from a provider-neutral notification contract.

The PyHookKit router is not a transparent proxy for arbitrary Slack payloads.
Adapt existing producers to the [canonical notification
contract](notification-parity.md). See the [central notification router
guide](central-notification-router.md) for this optional path.

## Next steps

- Add titles, facts, and actions with the [Teams Adaptive Card design
guide](teams-adaptive-cards.md).
- Compare Azure-managed alternatives in [Teams delivery
options](teams-delivery-options.md).
- Protect production credentials and callbacks with the [security
guide](security.md).
