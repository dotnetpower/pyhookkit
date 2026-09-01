# O10: Socket Mode

Opens one Slack Socket Mode connection, receives one event, acknowledges its
envelope, and exits.

```shell
uv run python slack_operations/10_socket_mode/slack.py
uv run python slack_operations/10_socket_mode/slack.py --listen-once
```

Live execution requires `SLACK_APP_TOKEN` with `connections:write` and the bot
token needed by the configured app. Slack-issued WebSocket URLs are short-lived
credentials and are never printed.
