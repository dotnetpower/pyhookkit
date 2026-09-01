# O04: Channel and broadcast mentions

Renders a Slack channel link and demonstrates an explicit allowlist for
`@here`, `@channel`, and `@everyone`.

```shell
uv run python slack_operations/04_mentions/slack.py
uv run python slack_operations/04_mentions/slack.py \
  --broadcast here --allow-broadcast
```

This example is render-only. A broadcast request fails unless the exact
audience is deliberately authorized with `--allow-broadcast`.
