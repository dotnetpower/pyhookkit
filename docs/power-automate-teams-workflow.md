# Power Automate Teams Workflow

This guide creates the Power Automate delivery adapter used by PyHookKit Teams
examples and the integrated Bookinfo scenario. It owns the manual provider
bootstrap, callback credential, Teams destination, smoke test, and operational
verification.

For the GitHub, GitLab, Argo CD, and AKS sequence, see the
[integrated Bookinfo scenario](integrated-bookinfo-scenario.md).

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
- a dedicated synthetic test Team and channel;
- permission to create protected GitLab CI/CD variables;
- Python 3.12 and `uv` for the smoke test.

Do not place real Team names, channel names, identities, or callback URLs in
committed files or screenshots.

## Create the flow

1. Open [Power Automate](https://make.powerautomate.com).
2. Select the environment that owns the Teams connection.
3. Select **Create**, then **Create from blank**.
4. Name the flow using an environment-neutral name such as
   `PyHookKit Teams Flow`.
5. Add the Microsoft Teams trigger **When a Teams webhook request is
   received**.
6. Set **Who can trigger the flow?** to **Anyone** for the signed callback URL
   model used by these examples.
7. Add **Post card in a chat or channel** directly after the trigger.

The completed flow has exactly one trigger and one action:

![Power Automate flow with Teams webhook trigger and post-card action](assets/power-automate-teams-workflow/power-automate-flow-designer.png)

## Configure the Teams action

Set the action fields as follows:

| Field | Value |
|---|---|
| **Post as** | `Flow bot` |
| **Post in** | `Channel` |
| **Team** | The dedicated synthetic test Team |
| **Channel** | The dedicated notification test channel |
| **Adaptive Card** | `triggerBody()` |

![Power Automate Teams post-card action settings](assets/power-automate-teams-workflow/power-automate-teams-action.png)

The current Teams Workflow trigger exposes the webhook body in the form
accepted by **Post card in a chat or channel**. Pass it directly:

```text
triggerBody()
```

This is the setting used by the verified live flow shown above. Do not use the
Azure Logic App expression from the separate Logic App adapter; that endpoint
accepts a different request contract.

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
7. Add a co-owner before using the flow as a shared or long-lived integration.

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

Confirm all three outcomes:

1. the card appears in the expected Teams channel;
2. the card has no owner attribution or **Get template** footer;
3. the corresponding Power Automate run is **Succeeded**.

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

Confirm that the Teams action is enabled, its connection is valid, and the
selected Team and channel still exist. Open the corresponding run and inspect
the trigger and action status without copying request bodies or connection
details into an issue.

### Power Automate rejects the request

Check that the caller sends the Teams `message` envelope expected by the
Workflow adapter. A Logic App request uses a different contract and cannot be
sent by replacing only the endpoint URL.

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
