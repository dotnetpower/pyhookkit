# Slack operations

These provider-specific examples complement the provider-neutral fundamentals.
They use Slack Web API capabilities that do not have a one-to-one Teams payload
equivalent, including workspace discovery and message lifecycle operations.

Every command is dry-run by default. Live API calls require an explicit flag
and credentials loaded from the repository `.env`.

| ID | Capability | Required bot scopes |
|---|---|---|
| O00 | Authentication check | none beyond a valid token |
| O01 | Channels and members | `channels:read`, `groups:read` |
| O02 | Users and user groups | `users:read`, `usergroups:read` |
| O03 | Message lifecycle | `chat:write` |
| O04 | Channel and broadcast mentions | `chat:write` |
| O05 | Interactive approval | `chat:write`; signing secret |
| O06 | File upload | `files:write` |
| O07 | Reactions | `chat:write`, `reactions:write` |
| O08 | Scheduled and ephemeral messages | `chat:write` |
| O09 | Events API HTTP | `app_mentions:read`; signing secret |
| O10 | Socket Mode | `app_mentions:read`; app token `connections:write` |

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
