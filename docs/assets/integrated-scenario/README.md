# Integrated scenario captures

These files are real client and control-plane captures from the disposable
Bookinfo staging scenario.

| File | Evidence |
|---|---|
| `azure-aks-resources.png` | Azure resources associated with the AKS example |
| `bookinfo-productpage.png` | Bookinfo workload response |
| `argocd-bookinfo-application.png` | Argo CD `Healthy` and `Synced` application |
| `github-approval-pending.png` | GitHub Environment approval gate |
| `github-approval-complete.png` | Approved and completed release workflow |
| `gitlab-promotion-pipeline.png` | GitOps validation and promotion |
| `gitlab-argocd-notification-pipeline.png` | Argo-triggered notification pipeline |
| `gitlab-incident-pipeline.png` | Incident notification pipeline |
| `gitlab-maintenance-pipeline.png` | Scheduled maintenance notification |
| `power-automate-flow-designer.png` | Webhook trigger and Teams action |
| `power-automate-teams-action.png` | Redacted Teams action configuration |
| `power-automate-flow-history.png` | Enabled flow and successful runs |
| `teams-approval-request.png` | Approval card received in Teams |

Captures are cropped to remove account, tenant, subscription, connection,
callback URL, Team, Channel, and other environment-specific identity details.
Do not replace the redacted images with uncropped originals.
