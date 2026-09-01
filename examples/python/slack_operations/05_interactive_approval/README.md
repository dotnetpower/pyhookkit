# O05: Interactive approval

Renders Slack `block_actions` approval buttons and provides a minimal signed
callback endpoint.

```shell
uv run python slack_operations/05_interactive_approval/slack.py
uv run python slack_operations/05_interactive_approval/slack.py --send
uv run python slack_operations/05_interactive_approval/callback.py --serve
```

Sending requires `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, and `chat:write`.
Callbacks require `SLACK_SIGNING_SECRET`; the server verifies the untouched
body, timestamp, and v0 signature before acknowledging an action.
