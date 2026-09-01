# O07: Reactions

Uses reactions as transient processing state on a synthetic message.

```shell
uv run python slack_operations/07_reactions/slack.py
uv run python slack_operations/07_reactions/slack.py --exercise
```

The live command posts a message, adds and removes the hourglass reaction, and
leaves a check-mark reaction. It requires `chat:write`, `reactions:write`, and
`SLACK_CHANNEL_ID`.
