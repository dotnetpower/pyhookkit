# Slack app manifest

`manifest.example.json` declares the synthetic capabilities used by the Slack
fundamentals and operations examples:

- `incoming-webhook` for F01-F08 and F10;
- `chat:write` for posting, threading, mutation, scheduling, and ephemeral
  messages;
- `channels:read` and `groups:read` for public and private conversation
  discovery;
- `users:read` and `usergroups:read` for mention identity discovery;
- `files:write` for the external file upload flow;
- `reactions:write` for status reactions;
- `reactions:read`, `channels:history`, and `groups:history` for subscribed
  reaction and message-deletion events;
- `app_mentions:read` for app mentions through Events API or Socket Mode.

Create a Slack app with **From a manifest**, select a development workspace,
paste the JSON, review the requested scopes, and create the app. Workspace
installation, channel selection, and issued credentials remain bootstrap
concerns.

The committed Request URLs use the reserved `pyhookkit.example` domain and must
be replaced before installing the manifest. For local development, expose the
loopback HTTP examples through an approved HTTPS tunnel or enable Socket Mode.
Socket Mode additionally requires an app-level token with `connections:write`;
app-level token scopes are configured when that token is generated.

The manifest intentionally does not request `users:read.email`. Display-name
discovery avoids collecting email addresses.
