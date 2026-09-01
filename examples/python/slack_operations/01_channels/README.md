# O01: Channels and members

Uses cursor-paginated `conversations.list` and `conversations.members` calls.
Private channels appear only when the bot already has access.

```shell
uv run python slack_operations/01_channels/slack.py
uv run python slack_operations/01_channels/slack.py --live
uv run python slack_operations/01_channels/slack.py --live --members C00000001
```

Live discovery requires `channels:read` and `groups:read`. Channel and member
IDs are environment data and must not enter canonical fixtures.
