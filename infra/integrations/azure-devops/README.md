# Azure DevOps notification integration

Azure DevOps can submit canonical notifications from Azure Pipelines or send
provider-native Service Hook payloads to the central router.

## Azure Pipelines path

Use `azure-pipelines.yml` when a pipeline can construct the canonical contract.
Create these variables:

| Variable | Storage | Purpose |
|---|---|---|
| `NOTIFICATION_ROUTER_URL` | Non-secret variable | Public HTTPS router base URL, or an internal URL for a self-hosted agent |
| `NOTIFICATION_ROUTER_TOKEN` | Secret variable or Key Vault-linked variable group | API key scoped to producer `azure-devops` and the intended route or target |

The optional `routerTargetId` parameter sends to one destination. Leave it
blank to fan out over `release-notifications`.

## Service Hooks path

Azure DevOps Service Hooks send a provider-native JSON envelope and cannot call
the canonical endpoint directly. Register an inbound integration first:

```shell
export AZURE_DEVOPS_WEBHOOK_PASSWORD="$(python -c \
  'import secrets; print(secrets.token_urlsafe(32))')"

uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-integration \
  --integration-id azure-build \
  --provider azure-devops \
  --producer azure-devops \
  --secret-env AZURE_DEVOPS_WEBHOOK_PASSWORD \
  --username pyhookkit \
  --route release-notifications
```

In Azure DevOps, open **Project settings** > **Service hooks**, create a
**Web Hooks** subscription, and choose **Build completed**. On **Action**, use:

- URL: `https://notify.example.test/v1/inbound/azure-devops/azure-build`
- Basic authentication username: `pyhookkit`
- Basic authentication password: the value of
  `AZURE_DEVOPS_WEBHOOK_PASSWORD`
- Resource details to send: **Minimal** unless the mapped event requires more

Use **Test** before selecting **Finish**. Azure DevOps requires a public HTTPS
endpoint and does not target localhost or special-use address ranges. For a
private router, use the Pipeline path with a self-hosted agent instead of a
Service Hook.

The receiver currently maps `build.complete` and
`ms.vss-release.deployment-completed-event`. Other event types are rejected
without storing their payload.

Never commit the API key or Basic authentication password. The router does not
log raw Service Hook payloads or authentication headers.
