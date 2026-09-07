# Power Automate Teams Workflow captures

[한국어](README.ko.md)

These redacted captures accompany the
[Power Automate Teams Workflow guide](../../power-automate-teams-workflow.md).

| File | Evidence |
|---|---|
| `create-service-account.png` | Enter the Teams notification service account basics in Microsoft 365 admin center |
| `shared-flow-overview.png` | Shared flow containing the Teams Webhook request trigger and channel card action |
| `team-member.png` | Empty target-Team member list before adding the service account |
| `team-member2.png` | Confirm the service account has the **Member** role after adding it |
| `channel-copy-link.png` | Select **Copy link** from the target Teams channel's **...** menu |
| `hello-world.png` | Delivered **Hello, world!** Adaptive Card in the Teams channel |
| `github-webhook.png` | Successful Adaptive Card delivered to Teams from a GitHub `workflow_run` Webhook |
| `azure-portal-entra.png` | Search for and select **Microsoft Entra ID** in Azure Portal |
| `app-registration.png` | Microsoft Graph application permission and admin-consent status for `TeamsNotifyApp` |
| `automated-cloud-flow.png` | Power Automate **Automated cloud flow** selection tile |
| `automated-cloud-flow-skip.png` | **Skip** selection in the **Build an automated cloud flow** dialog |
| `flow-name-add-trigger.png` | Flow naming and **Add a trigger** selection |
| `microsoft-teams-webhook-trigger.png` | **Microsoft Teams Webhook** connector and webhook-request trigger selection |
| `teams-webhook-trigger-anyone.png` | Webhook trigger **Anyone** setting and post-save HTTP URL generation guidance |
| `add-post-card-action.png` | Add the Microsoft Teams post-card action below the trigger |
| `select-team-custom-value.png` | Select **Enter custom value** in the Teams post-card action |
| `enter-team-expression.png` | Enter the dynamic Team expression in the Teams post-card action |
| `teams-action-complete.png` | Final Teams post-card expressions and connection-user verification |
| `microsoft-365-service-account.svg` | Synthetic Teams connection service account in the Microsoft 365 admin center |
| `power-automate-flow-designer.png` | Webhook trigger and Teams action |
| `power-automate-teams-action.png` | Teams action configuration |
| `power-automate-flow-history.png` | Enabled flow and successful runs |

Team, channel, account, connection, environment, and callback URL values are
removed or replaced with synthetic values. `create-service-account.png` and
`shared-flow-overview.png` are attached PNGs saved without editing. Do not
replace these files with originals that contain credentials or real tenant
information.
