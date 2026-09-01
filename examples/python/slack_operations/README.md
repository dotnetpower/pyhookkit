# Slack operations

These provider-specific examples complement the provider-neutral fundamentals.
They use Slack Web API capabilities that do not have a one-to-one Teams payload
equivalent, including workspace discovery and message lifecycle operations.

Every command is dry-run by default. Live API calls require an explicit flag
and credentials loaded from the repository `.env`.

| ID | Capability | Required bot scopes |
|---|---|---|
| O00 | [Authentication check](00_auth_test/README.md) | none beyond a valid token |
| O01 | [Channels and members](01_channels/README.md) | `channels:read`, `groups:read` |
| O02 | [Users and user groups](02_identities/README.md) | `users:read`, `usergroups:read` |
| O03 | [Message lifecycle](03_message_lifecycle/README.md) | `chat:write` |
| O04 | [Channel and broadcast mentions](04_mentions/README.md) | render-only |
| O05 | [Interactive approval](05_interactive_approval/README.md) | `chat:write`; signing secret |
| O06 | [File upload](06_file_upload/README.md) | `files:write` |
| O07 | [Reactions](07_reactions/README.md) | `chat:write`, `reactions:write` |
| O08 | [Scheduled and ephemeral messages](08_scheduled_ephemeral/README.md) | `chat:write` |
| O09 | [Events API HTTP](09_events_http/README.md) | `app_mentions:read`; signing secret |
| O10 | [Socket Mode](10_socket_mode/README.md) | `app_mentions:read`; app token `connections:write` |

Private conversations are visible only when the token has access. Discovery
uses cursor pagination and intentionally does not request email addresses.

O05 includes both the interactive message publisher and a signed callback
server. O09 exposes a signed HTTP event endpoint. O10 uses a short-lived
Slack-issued WebSocket URL and acknowledges one Socket Mode envelope.

O09 accepts app mentions, reactions, message events such as deletion,
uninstallation, and token revocation. Configure only the subscriptions needed
in production. O08 immediately deletes its synthetic scheduled message;
scheduled delivery is limited by Slack. Ephemeral delivery is non-persistent,
requires an active channel member, and is not guaranteed.
