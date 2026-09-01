# O03: Message lifecycle

Exercises `chat.postMessage`, a threaded reply, `chat.update`, and
`chat.delete` while retaining Slack message references.

```shell
uv run python slack_operations/03_message_lifecycle/slack.py
uv run python slack_operations/03_message_lifecycle/slack.py --exercise
```

The live exercise requires `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, and
`chat:write`. It deletes the synthetic reply but leaves the updated parent
message as evidence.
