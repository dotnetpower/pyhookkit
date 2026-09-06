# Central router SQLite data model

[한국어](central-router-sqlite-data-model.ko.md)

This guide describes how the optional central notification router stores routes,
notifications, and per-target delivery state in SQLite. The source of truth for
table definitions is
[`SqliteRouteStore._initialize()`](../examples/python/src/pyhookkit/adapters/outbound/sqlite_route_store.py#L405-L454).

## Database creation and location

The path passed to `notification_router` with `--database` is the database
location. The documentation examples use
`examples/python/.local/router.sqlite3`. When `SqliteRouteStore` first opens, it
creates the required tables and indexes and sets the database file mode to
`0600`.

SQLite connections enable foreign-key checks and use WAL mode. To back up an
active database, use the SQLite backup API or stop the process and handle the
database and related WAL files together.

> [!NOTE]
> SQLite is the default implementation for the single-process example. If your
> organization prefers PostgreSQL, SQL Server, or another database, use this
> data model as a reference and replace the adapter. This repository currently
> ships only the SQLite adapter, so passing another database connection string
> to `--database` is not sufficient. Implement a store against
> [`NotificationRouteStore`](../examples/python/src/pyhookkit/ports/notification_routing.py#L15-L51)
> and wire it into the composition root. Preserve atomic notification and
> target creation, `(producer, event_id)` idempotency, per-target state,
> delivery leasing, and referential integrity.

## Table relationships

```text
route_destinations 1 ───< target_deliveries >─── 1 routed_notifications
      destination             target delivery          notification

producer_api_keys                    inbound_integrations
scoped credential digests            provider routing and secret references
```

One canonical notification creates one `target_deliveries` record for every
enabled destination on its route.

## `route_destinations`

Stores channel-specific notification destinations and provider routing
metadata.

| Column | Constraint | Meaning |
|---|---|---|
| `target_id` | Primary key | Lower-case kebab-case destination identifier |
| `route` | Required | Logical route from the canonical notification |
| `provider` | Required | `slack` or `teams-workflow` |
| `endpoint_environment_variable` | Required | Name of the environment variable holding the URL, not the credential itself |
| `channel_link` | Optional | Registered Teams channel link; `NULL` for Slack |
| `tenant_id` | Optional | Teams tenant ID derived from the channel link |
| `team_id` | Optional | Team ID derived from the link's `groupId` |
| `channel_id` | Optional | Teams channel ID derived from the channel link |
| `channel_name` | Optional | Channel display name derived from the channel link |
| `membership_type` | Optional | Graph-resolved `standard` or `private` channel type |
| `enabled` | `0` or `1` | Whether the destination is active |

An index on `(route, enabled)` finds active destinations during submission.
Registering an existing `target_id` updates that destination.

## `routed_notifications`

Stores provider-neutral notifications accepted by the central router.

| Column | Constraint | Meaning |
|---|---|---|
| `notification_id` | Primary key | Router-generated notification UUID |
| `producer` | Required | Name of the submitting producer |
| `event_id` | Required | Producer-supplied idempotency ID |
| `payload_json` | Required | Validated canonical notification JSON |
| `created_at` | Required | UTC creation timestamp |

`(producer, event_id)` is unique. Repeating the same payload with the same
producer and `event_id` returns the existing notification. Reusing the key with
a different payload is rejected as a conflict.

## `target_deliveries`

Stores independent delivery state for each notification destination.

| Column | Constraint | Meaning |
|---|---|---|
| `notification_id` | Composite primary key, foreign key | Notification in `routed_notifications` |
| `target_id` | Composite primary key, foreign key | Destination in `route_destinations` |
| `state` | Required | One of `queued`, `delivering`, `succeeded`, or `failed` |
| `attempts` | At least 0 | Number of completed delivery attempts |
| `error_kind` | Optional | Stable, redacted error classification |
| `status_code` | Optional | HTTP status returned by the provider |
| `locked_at` | Optional | Time at which a worker leased the delivery |
| `updated_at` | Required | Last state-change timestamp |

An index on `(state, updated_at)` finds work and expired leases. A worker leases
`queued` records by moving them to `delivering`; expired leases return to
`queued`. Completion changes the state to `succeeded` or `failed`. Delivery is
therefore at least once, and a process failure immediately after provider
success can produce a duplicate message.

## `producer_api_keys`

Stores non-reversible SHA-256 digests and redacted lifecycle metadata for
server-issued API keys. `key_id` is safe to list, while the raw `phk_` value is
returned only at issuance. A key is restricted to either one `route` or one
`target_id`. `revoked_at` disables it and `last_used_at` supports operational
review without retaining request content.

## `inbound_integrations`

Stores provider, producer, fixed route, optional target, Basic username when
needed, and the name of the environment variable holding the provider
authentication secret. It never stores GitHub Webhook secrets, GitLab signing
tokens, or Azure DevOps Basic passwords. `last_received_at` records only the
time of a successfully authenticated event.

## Initialization and migration

There is no external SQL migration file or schema-version table. Startup uses
`CREATE TABLE IF NOT EXISTS`, then automatically adds missing Teams metadata
columns to older `route_destinations` tables. See
[`_migrate_destination_metadata()`](../examples/python/src/pyhookkit/adapters/outbound/sqlite_route_store.py#L456-L493)
for the implementation.

Back up the database before a schema change and run `doctor` with the new code to
verify routes and memberships. Do not edit an active database directly.

## Stored data and security

SQLite does not store these secrets:

- Slack Webhook URLs;
- signed Teams Workflow URLs;
- raw router producer API keys;
- provider Webhook signing secrets and Basic passwords;
- `TeamsNotifyApp` client secrets.

Instead, destination and inbound integration records store only environment
variable names. Server-issued producer keys store SHA-256 digests because their
256-bit random values are not recoverable from the digest. Keep provider
secrets and legacy producer tokens in the Git-ignored repository-root `.env` or
a deployment secret store.

SQLite does store Teams channel links and each canonical notification's
`payload_json`. Do not put secrets or unnecessary personal data in notification
content. This example has no automatic retention period or purge job, so a
production deployment needs a cleanup procedure aligned with organizational
data-retention policy.

## Inspect the live schema

Use the Python standard library to inspect DDL without an external `sqlite3`
CLI. Run this command from `examples/python`. It does not print row data or
credentials.

```shell
python3 - <<'PY'
import sqlite3
from pathlib import Path

path = Path(".local/router.sqlite3").resolve()
with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
    rows = connection.execute(
        """
        SELECT type, name, sql
        FROM sqlite_master
        WHERE type IN ('table', 'index') AND sql IS NOT NULL
        ORDER BY type DESC, name
        """
    )
    for object_type, name, sql in rows:
        print(f"-- {object_type}: {name}\n{sql};\n")
PY
```

## Related information

- [Central notification router](central-notification-router.md)
- [TeamsNotifyApp bootstrap](teams-notify-app-bootstrap.md)
- [Security guide](security.md)
