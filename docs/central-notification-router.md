# Central notification router

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

For administrator-controlled registration, ensure that the dedicated Teams
connection user belongs to the target Team before the destination is stored:

```shell
export TEAMS_CONNECTION_USER="<Entra object ID or UPN>"
export TEAMS_TENANT_ID="<expected tenant GUID>"
export MICROSOFT_GRAPH_ACCESS_TOKEN="<short-lived Graph token>"

uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id teams-release \
  --route release-notifications \
  --provider teams-workflow \
  --endpoint-env TEAMS_WORKFLOW_URL \
  --channel-link "$TEAMS_WORKFLOW_CHANNEL_LINK" \
  --ensure-team-membership
```

The Graph principal requires `GroupMember.ReadWrite.All` or the broader
`Group.ReadWrite.All` with administrator consent. The channel link's `groupId`
identifies the Team's backing Microsoft 365 Group. Prefer the connection user's
Entra object ID; resolving a UPN additionally requires permission to read that
user. The command adds only a normal member, never an owner. It first checks
existing members, making repeated registration idempotent. A tenant mismatch,
Graph denial, or malformed response prevents the destination from being
configured.

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
Inspect non-secret configuration with:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  list-destinations
```

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
