# Power Automate Teams Workflow

This guide creates the Power Automate delivery adapter used by PyHookKit Teams
examples and the integrated Bookinfo scenario. One flow accepts a validated
Teams channel link and Adaptive Card message, extracts the Team and Channel
identifiers, and posts to an approved destination.

For the GitHub, GitLab, Argo CD, and AKS sequence, see the
[integrated Bookinfo scenario](integrated-bookinfo-scenario.md).
For direct Team and Channel ID routing with an Azure-managed workflow, use the
[Azure Logic App Teams delivery guide](logic-app-teams-delivery.md).

## Why create the flow from blank

Use a flow created from blank rather than the **Send webhook alerts to a
channel** gallery template.

Live testing established that both flows render rich Adaptive Cards and native
user mentions. The gallery template additionally injects owner attribution and
a **Get template** footer outside the Adaptive Card payload. Payload changes
cannot remove it. A from-blank flow has no **Original template** relationship
and avoided that footer in the verified environment.

## Prerequisites

- permission to create a Power Automate cloud flow;
- a Microsoft Teams connection authorized for the destination Team;
- a dedicated licensed Microsoft 365 connection user for shared or production
   environments;
- one or more dedicated synthetic test Teams channels that the connection user
   can access;
- permission to create protected GitLab CI/CD variables;
- Python 3.12 and `uv` for the smoke test.

Do not place real Team names, channel names, identities, or callback URLs in
committed files or screenshots.

## Create the flow

1. Open [Power Automate](https://make.powerautomate.com).
2. Select the environment that owns the Teams connection.
3. Select **Create**, then **Create from blank**.
4. Name the flow using an environment-neutral name such as
   `PyHookKit Routed Teams Flow`.
5. Add the Request trigger **When an HTTP request is received** and paste the
   contents of `routed-request.schema.json` into **Request Body JSON Schema**.
6. Set **Who can trigger the flow?** to **Anyone** for the signed callback URL
   model used by these examples. **Specific users in my tenant** is stronger,
   but requires an OAuth-capable caller that is outside the current callback
   client contract.
7. Add the flow to a Solution and create a text environment variable with the
   schema name `pyk_AllowedChannelLinks`.
8. Set its current value to a JSON array containing the exact approved Teams
   channel links. Keep real links out of source control.

The routed request contract is
[`routed-request.schema.json`](../infra/teams-workflows/routed-request.schema.json).
Its top-level `channelLink` carries routing and its `attachments` collection
carries the message. The existing screenshot shows the earlier fixed-channel
shape and should not be used as the routed-flow definition:

![Power Automate flow with Teams webhook trigger and post-card action](assets/power-automate-teams-workflow/power-automate-flow-designer.png)

## Validate and parse the destination

Add a **Compose** action named `Channel_link`:

```text
triggerBody()?['channelLink']
```

Before parsing the URL, add a **Condition** that checks the exact link against
the Solution environment-variable allowlist. Insert the
`pyk_AllowedChannelLinks` dynamic value in place of the placeholder:

```text
contains(json(<Allowed channel links>), outputs('Channel_link'))
```

In the **False** branch, add **Terminate** with status `Failed`, code
`DestinationNotAllowed`, and a generic message that does not echo the supplied
link. This check must precede the Teams action. Restrict the dedicated Teams
connection user to notification Teams as an additional authorization boundary.

In the **True** branch, add `Team_ID` and `Channel_ID` Compose actions.

`Team_ID`:

```text
first(split(last(split(uriQuery(outputs('Channel_link')), 'groupId=')), '&'))
```

`Channel_ID`:

```text
decodeUriComponent(first(split(last(split(uriPath(outputs('Channel_link')), '/l/channel/')), '/')))
```

The deployment tooling validates every allowlisted link as an HTTPS
`teams.microsoft.com/l/channel/...` URL with one GUID `groupId`, one GUID
`tenantId`, and a supported channel ID before import.

## Configure the Teams action

Add **Post card in a chat or channel** to the Condition's **True** branch. For
the Team and Channel controls, select **Enter custom value** and use the Compose
outputs:

Set the action fields as follows:

| Field | Value |
|---|---|
| **Post as** | `Flow bot` |
| **Post in** | `Channel` |
| **Team** | `outputs('Team_ID')` |
| **Channel** | `outputs('Channel_ID')` |
| **Adaptive Card** | `first(triggerBody()?['attachments'])?['content']` |

![Power Automate Teams post-card action settings](assets/power-automate-teams-workflow/power-automate-teams-action.png)

Do not pass the complete trigger body into the Adaptive Card field. The routed
body also contains `channelLink`; only the first attachment's `content` object
is the Adaptive Card. Private-channel posting remains unsupported by the Teams
connector.

## Save and store the callback

1. Select **Save**.
2. Reopen the trigger and copy its generated **HTTP URL**.
3. Treat the complete URL as a credential because its query string contains the
   callback signature.
4. In GitLab, open **Settings → CI/CD → Variables**.
5. Add the callback with:
   - key: `TEAMS_WORKFLOW_URL`;
   - visibility: **Masked**;
   - protection: **Protected**;
   - expansion: disabled.
6. Do not store the URL in GitHub, Argo CD, Kubernetes manifests, screenshots,
   command output, or repository files.
7. Store the selected channel link as `TEAMS_WORKFLOW_CHANNEL_LINK` in the same
   protected environment. It is configuration rather than a credential, but it
   contains real tenant and destination identifiers.
8. Add at least two named operational co-owners before using the flow as a
   shared or long-lived integration.

## Smoke test

From `examples/python`, render before sending:

```shell
uv run python scenarios/deployment_result/teams.py
```

Verify that the payload contains only synthetic data. Then load the ignored
local environment and send deliberately:

```shell
set -a
. ../../.env
set +a
uv run python scenarios/deployment_result/teams.py --send
```

The CLI must return:

```json
{
  "state": "succeeded",
  "attempts": 1
}
```

Confirm all four outcomes:

1. the card appears in the expected Teams channel;
2. a non-allowlisted synthetic link reaches `DestinationNotAllowed` without a
   Teams connector call;
3. the card has no owner attribution or **Get template** footer;
4. the corresponding Power Automate run is **Succeeded**.

## Runtime evidence

The verified flow is enabled. Its run history shows the webhook requests used
by the integration scenarios completing successfully.

![Power Automate flow details and successful run history](assets/power-automate-teams-workflow/power-automate-flow-history.png)

## Troubleshooting

### The card has a Get template footer

Open the flow details page and check for **Original template**. Recreate the
flow from blank if that relationship exists. Renaming the flow, changing the
Adaptive Card, or copying the callback URL does not remove template metadata.

### The request succeeds but no card appears

Confirm that the link exactly matches an allowlist entry, the Teams action is
enabled, its connection is valid, and the connection user can access the Team
and channel. Open the corresponding run and inspect action status without
copying request bodies or connection details into an issue.

### Power Automate rejects the request

Check that the caller sends `channelLink` alongside the Teams `message`
envelope expected by the Workflow adapter. A Logic App request uses direct IDs
and cannot be sent by replacing only the endpoint URL.

### Images do not render

Teams must fetch image URLs over public HTTPS. Runtime sends resolve committed
synthetic markers through `EXAMPLE_ASSET_BASE_URL`.

## Lifecycle and automation

The first flow requires selecting and authorizing a Microsoft connection. For
repeated environments, place the verified flow in a Power Platform Solution,
replace concrete connections with connection references, and deploy with Power
Platform CLI.

The generated callback URL remains environment-specific runtime state. Retrieve
it after activation and write it directly to the target secret store.

See the [Teams Workflows infrastructure
runbook](../infra/teams-workflows/README.md) for the ALM roadmap, ownership
requirements, and footer verification checklist.
