# O00: Authentication check

Calls `auth.test` to verify `SLACK_BOT_TOKEN` without printing the token.

```shell
uv run python slack_operations/00_auth_test/slack.py
uv run python slack_operations/00_auth_test/slack.py --live
```

The default command prints the planned method only. Live output contains the
workspace and authenticated bot identities; do not commit it.
