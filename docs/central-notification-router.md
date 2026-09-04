# Central notification router

[한국어](central-notification-router.ko.md)

The central router is an optional SQLite-backed example for sending the same
canonical notification from GitLab, Argo CD, or another producer through one
routing boundary. Existing direct Slack and Teams commands remain available for
local testing, migration, and a deliberately selected fallback.

```text
GitLab ──────┐
Argo CD ─────┼── canonical JSON ──> router ──> SQLite outbox
other source ┘                                  ├─ Slack webhook
                                                └─ Teams Workflow
```

The router owns fan-out. Power Automate still receives one destination per
request and remains a Teams delivery adapter rather than a routing database.

## Scope

The example provides:

- strict canonical notification parsing;
- producer-specific bearer credentials;
- route-to-many-destinations configuration;
- transactional SQLite notification and target-delivery records;
- idempotency for each producer and `eventId`;
- an at-least-once leased worker;
- redacted aggregate and per-target delivery status;
- existing Slack and Teams renderer and retry-policy reuse.

It intentionally omits an administration API, automatic identity lookup,
dead-letter replay UI, and multi-node worker coordination. SQLite is suitable
for this single-process example and modest notification volume. Use a
queue-backed store before running multiple router replicas.

## Initialize routes

Run commands from `examples/python`. Database and credential files are ignored
by Git.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  init-db
```

Add a Slack destination. The database stores only the environment variable
name, not its webhook value:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id slack-release \
  --route release-notifications \
  --provider slack \
  --endpoint-env SLACK_WEBHOOK_URL
```

Add a Teams destination by supplying an approved channel link. The signed
Workflow URL remains outside SQLite:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id teams-release \
  --route release-notifications \
  --provider teams-workflow \
  --endpoint-env TEAMS_WORKFLOW_URL \
  --channel-link "$TEAMS_WORKFLOW_CHANNEL_LINK"
```

## Bootstrap TeamsNotifyApp

Use a visible, single-tenant `TeamsNotifyApp` registration instead of persisting
an Azure CLI delegated token. Sign in to the channel tenant once:

The complete identity, minimum-role, rotation, and recovery runbook is in
[TeamsNotifyApp bootstrap](teams-notify-app-bootstrap.md).

```shell
az login \
  --tenant "<channel tenant ID>" \
  --use-device-code \
  --allow-no-subscriptions
```

Then run:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  bootstrap-teams-app \
  --channel-link "$TEAMS_WORKFLOW_CHANNEL_LINK" \
  --connection-user "svc-teams-notification@example.com" \
  --route release-notifications \
  --target-id teams-release
```

The command:

1. derives the tenant and Team IDs from the channel link;
2. creates or uniquely reuses `TeamsNotifyApp`;
3. creates its tenant Service Principal;
4. resolves the Microsoft Graph application-role ID dynamically;
5. adds `GroupMember.ReadWrite.All` and grants tenant-wide admin consent;
6. resolves the connection user once through the bootstrap identity;
7. creates a one-year client secret when no reusable local credential exists;
8. proves that client credentials issue a matching app-only Graph token;
9. adds the connection user to the Team's backing Microsoft 365 Group;
10. writes the app identifiers and secret atomically to the repository `.env`
    with mode `0600`;
11. registers the destination in SQLite.

The client secret is never printed. Re-run with `--rotate-secret` to create and
store a replacement credential. Remove obsolete credentials in the Entra portal
after the replacement succeeds.

### Minimum bootstrap permissions

| Task | Identity | Least privilege |
|---|---|---|
| Create the app registration | Bootstrap app creator | No directory role when tenant policy permits users to register apps; otherwise **Application Developer** |
| Manage the newly created app and credential | App creator/owner | Ownership of `TeamsNotifyApp`; use **Cloud Application Administrator** only when a separate operator must manage applications it does not own |
| Grant Microsoft Graph application permission | Consent approver | **Privileged Role Administrator**, activated only for bootstrap through PIM where available |
| Create and edit the Flow | Flow author | Power Platform **Environment Maker** in the target environment |
| Authorize the Teams connector | `svc-teams-notification` | Licensed Microsoft 365/Teams and Power Automate user; no Entra administrator role |
| Add Team memberships at runtime | `TeamsNotifyApp` service principal | Microsoft Graph application permission `GroupMember.ReadWrite.All` |
| Submit notifications | GitLab, Argo CD, or another producer | Router bearer credential only; no Graph or Power Platform role |

Microsoft Graph application permissions require tenant-wide admin consent.
**Privileged Role Administrator** is the least privileged built-in role that can
grant consent for Microsoft Graph app roles. Global Administrator also works
but is intentionally not the recommended bootstrap role.

The user running the complete automated command therefore needs both permission
to create an app registration and an active Privileged Role Administrator role.
These duties can be separated operationally, but the current one-command
bootstrap expects both capabilities to be active.

Microsoft references:

- [least-privileged roles by task](https://learn.microsoft.com/entra/identity/role-based-access-control/delegate-by-task);
- [grant tenant-wide admin consent](https://learn.microsoft.com/entra/identity/enterprise-apps/grant-admin-consent);
- [application and Service Principal objects](https://learn.microsoft.com/entra/identity-platform/app-objects-and-service-principals);
- [add a Microsoft 365 Group member](https://learn.microsoft.com/graph/api/group-post-members?view=graph-rest-1.0).

The identity must be the same account bound to the Power Automate Teams
connection. Adding a Flow co-owner does not change the connector execution
identity. Standard-channel access follows Team membership. Private and shared
channels can require explicit channel membership, and Flow bot delivery to a
private channel remains unsupported.

Registration accepts current `teams.cloud.microsoft` channel links and legacy
`teams.microsoft.com` links. The router stores the original link plus derived
tenant ID, Team ID, channel ID, and channel name in separate columns. Delivery
sends a Teams `message` envelope with top-level `teamId` and `channelId` plus
one Adaptive Card attachment; it does not send the channel link or callback URL.

Repeat `add-destination` with another unique target ID to fan out one route.
The repository `.env` is loaded automatically. With TeamsNotifyApp configured,
the command acquires a fresh app-only token rather than reading a saved Graph
access token:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id teams-another-channel \
  --route release-notifications \
  --provider teams-workflow \
  --endpoint-env TEAMS_WORKFLOW_URL \
  --channel-link "<Teams channel link>" \
  --ensure-team-membership
```

Inspect non-secret configuration with:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  list-destinations
```

Verify the complete local setup without sending a notification:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  doctor
```

`doctor` validates the Workflow URL, obtains and validates an app-only Graph
token, verifies the connection user's membership in every enabled Team, and
checks the SQLite file's owner-only mode. It never prints credentials.

## Run locally

Create a different random token for every producer and inject provider
credentials from the ignored `.env` or another secret store.

```shell
export PYHOOKKIT_GITLAB_ROUTER_TOKEN="$(python -c \
  'import secrets; print(secrets.token_urlsafe(32))')"
export PYHOOKKIT_ARGOCD_ROUTER_TOKEN="$(python -c \
  'import secrets; print(secrets.token_urlsafe(32))')"

uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  serve \
  --producer gitlab=PYHOOKKIT_GITLAB_ROUTER_TOKEN \
  --producer argocd=PYHOOKKIT_ARGOCD_ROUTER_TOKEN
```

The process exposes:

- `GET /healthz`;
- `POST /v1/notifications`;
- `GET /v1/notifications/{notificationId}`.

The POST endpoint returns `202` after SQLite commits the notification and all
target records. Delivery occurs in the worker; `202` is not provider delivery
evidence. Query the returned notification ID for `queued`, `delivering`,
`delivered`, `partial_failed`, or `failed`.

Submit a committed synthetic contract:

```shell
export NOTIFICATION_ROUTER_URL=http://127.0.0.1:8080
export NOTIFICATION_ROUTER_TOKEN="$PYHOOKKIT_GITLAB_ROUTER_TOKEN"

uv run python -m pyhookkit.entrypoints.notification_router_client \
  --producer gitlab \
  --input ../../contracts/test-vectors/scenarios/deployment-result/notification.json
```

Remote clients require HTTPS. Loopback HTTP is accepted only for local
development.

## GitLab and Argo CD

GitLab pipeline input `notification-path` selects `direct` or `router`. Keep
`direct` during migration; select `router` after configuring the protected,
masked `NOTIFICATION_ROUTER_URL` and `NOTIFICATION_ROUTER_TOKEN` variables.

Argo CD includes separate `bookinfo-router-sync-failed` and
`bookinfo-router-sync-succeeded` templates. To bypass GitLab notification
dispatch, configure the synthetic router URL, create the
`notification-router-token` secret key, and change each trigger's `send` entry
to the corresponding router template. Do not enable both template paths for the
same event.

## Delivery guarantees and limitations

Duplicate submissions from one producer return the original notification ID.
Reusing that producer's `eventId` with different content returns a conflict.
Each configured destination has an independent terminal result, so one failed
channel produces `partial_failed` rather than hiding successful channels.

The worker recovers an expired delivery lease. A process failure after the
provider accepted a message but before SQLite stored success can therefore
produce a duplicate provider message. Slack and Teams webhook delivery do not
offer a shared transactional idempotency key. Consumers must treat `eventId`
and the visible correlation ID as the duplicate-detection reference.

Do not place tokens, signed callback URLs, canonical payloads, or provider
responses in logs. The HTTP transport suppresses request logs, and persisted
delivery errors contain only stable classifications and optional HTTP status.
