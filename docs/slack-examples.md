# Slack examples

The Slack reference progresses from a dependency-free HTTP request through
library-backed rendering to explicit Web API boundaries. Run commands from
`examples/python`.

## Raw HTTP bootstrap

F00 uses Python's standard library rather than `pyhookkit`. It renders the
request by default and sends only when `--send` is supplied:

```shell
python fundamentals/00_http_request/slack.py
python fundamentals/00_http_request/slack.py --send
```

## Rendering and sending

F01-F07 and F10 render JSON by default:

```shell
uv run python fundamentals/03_rich_card/slack.py
```

After loading the repository root `.env`, add `--send` to deliberately deliver
an Incoming Webhook message:

```shell
uv run python fundamentals/03_rich_card/slack.py --send
```

Use `--check-route` to validate that `SLACK_WEBHOOK_URL` is present and belongs
to Slack without printing it:

```shell
uv run python fundamentals/07_routing/slack.py --check-route
```

## Catalog

| ID | Example | Slack behavior | Live requirement |
|---|---|---|---|
| F00 | Raw HTTP request | Standard-library JSON POST | Incoming Webhook |
| F01 | Hello World | Minimal `text` payload | Incoming Webhook |
| F02 | Basic notification | Header, body, severity color, timestamp | Incoming Webhook |
| F03 | Rich card | Block Kit facts and context | Incoming Webhook |
| F04 | Mention | User and user-group alias resolution | Incoming Webhook plus configured identity IDs |
| F05 | Link and action | HTTPS `button` action | Incoming Webhook |
| F06 | Image | External HTTPS image and alt text | Incoming Webhook and publicly reachable image |
| F07 | Routing | Logical route resolved at the entrypoint | Incoming Webhook environment mapping |
| F08 | Thread or reply | Adds a known parent `thread_ts` | Persisted parent timestamp |
| F09 | Update and delete | Renders `chat.update` and `chat.delete` bodies | Web API bot token; sending not yet enabled |
| F10 | Error and retry | Redacted classification and bounded retry | Incoming Webhook |

## Web API and inbound operations

Provider-specific operational examples live under
`examples/python/slack_operations`. They are dry-run by default:

```shell
uv run python slack_operations/00_auth_test/slack.py --live
uv run python slack_operations/01_channels/slack.py --live
uv run python slack_operations/02_identities/slack.py \
  --live --display-name example-owner
uv run python slack_operations/03_message_lifecycle/slack.py --exercise
```

The identity example can append `--send-mention` after confirming the resolved
member. Committed defaults never contain a real display name or Slack ID.

| ID | Operation | Slack API / behavior |
|---|---|---|
| O00 | Authentication | `auth.test` without exposing the token |
| O01 | Channels and members | Cursor-paginated `conversations.list/members` |
| O02 | Identity discovery | `users.list`, `usergroups.list`, optional mention |
| O03 | Message lifecycle | Post, reply, update, and delete with retained `ts` |
| O04 | Channel/broadcast mentions | Channel link plus explicit broad-mention allowlist |
| O05 | Interactive approval | Block actions, HMAC signature and replay verification |
| O06 | File upload | External upload URL, binary upload, completion |
| O07 | Reactions | Add/remove processing state |
| O08 | Scheduled/ephemeral | Schedule/delete and user-targeted ephemeral message |
| O09 | Events HTTP | Signed URL verification and event acknowledgment |
| O10 | Socket Mode | Open WebSocket, receive once, acknowledge envelope |

Private channels appear only when the token has access. Collection examples
follow `next_cursor`; they do not assume that one API response is complete.
`chat.postMessage` responses are parsed separately from Incoming Webhook
responses because Slack Web API failures can return HTTP 200 with
`{"ok": false}`.

## Mention configuration

The committed F04 output uses synthetic Slack identifiers. Before sending F04,
set real test identities in the ignored `.env`:

```dotenv
SLACK_USER_ID="<test Slack member ID>"
SLACK_USER_GROUP_ID="<test Slack user-group ID>"
```

Find a member ID from the user's Slack profile menu using **Copy member ID**.
Find a user-group ID through an approved directory/configuration process. The
example rejects `--send` when either variable is blank so it cannot silently
pretend that a synthetic mention worked.

The canonical input retains only `example-owner` and `example-responders`.
Provider identifiers remain inside the Slack composition boundary.

## Thread, update, and delete boundary

Incoming Webhooks return `ok` but not the posted message timestamp. F08
therefore demonstrates rendering with a previously stored synthetic parent
reference.

F09 is intentionally render-only. Live update and delete operations require:

- `SLACK_BOT_TOKEN` with `chat:write`;
- `SLACK_CHANNEL_ID`;
- the `ts` returned by a message originally authored by that bot.

Do not use a Web API mutation against messages owned by another app or user.

## Reliability behavior

The F10 destination:

- sets explicit connect, read, write, and pool timeouts;
- honors `Retry-After` before exponential backoff;
- adds jitter, caps exponential delay and provider-directed waits separately,
  and limits attempt count;
- retries transport errors, `429`, and transient `5xx`;
- does not retry invalid payload, authentication, permission, or permanent
  provider errors;
- returns a provider-neutral result without the webhook URL, raw request, or
  response body.

Web API calls apply the same bounded `Retry-After` behavior while classifying
Slack JSON error codes. Posting and Incoming Webhooks should be paced at about
one message per second per channel; exact burst tolerance must not be assumed.

## Interactive and event delivery

O05 renders real `block_actions` buttons and includes a callback server that
verifies Slack's v0 HMAC signature against the untouched request body. O09
implements the same verification for Events API URL challenges and callbacks.
Both reject requests older than five minutes. O10 is the alternative Socket
Mode path for development behind a firewall; it requires `SLACK_APP_TOKEN`.

## Files

O06 uses the current sequence:

1. `files.getUploadURLExternal`;
2. binary POST to the Slack-issued `files.slack.com` URL;
3. `files.completeUploadExternal`.

The retired `files.upload` method is intentionally not demonstrated.

## Provider limits

The renderer keeps Slack limits explicit:

- long body text is split across section blocks;
- facts are split into groups of ten fields;
- button labels are limited to 75 characters;
- header titles are limited to 150 characters;
- rendered `mrkdwn` facts that exceed Slack's 2,000-character field limit fail
  explicitly instead of producing a provider rejection;
- navigation actions accept HTTPS URLs only;
- image alt text is mandatory;
- missing identity mappings fail instead of dropping mentions.

See the
[Slack Incoming Webhooks documentation](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks)
and [`chat.update`](https://docs.slack.dev/reference/methods/chat.update) /
[`chat.delete`](https://docs.slack.dev/reference/methods/chat.delete) references.
Operational examples follow the official
[`conversations.list`](https://docs.slack.dev/reference/methods/conversations.list/),
[message formatting](https://docs.slack.dev/messaging/formatting-message-text/),
[request verification](https://docs.slack.dev/authentication/verifying-requests-from-slack/),
[Socket Mode](https://docs.slack.dev/apis/events-api/using-socket-mode/), and
[rate-limit](https://docs.slack.dev/apis/web-api/rate-limits/) guidance.
