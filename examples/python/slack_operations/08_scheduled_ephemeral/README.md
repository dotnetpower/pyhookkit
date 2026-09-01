# O08: Scheduled and ephemeral delivery

Schedules and immediately deletes a synthetic reminder, then posts an
ephemeral confirmation to one active channel member.

```shell
uv run python slack_operations/08_scheduled_ephemeral/slack.py
uv run python slack_operations/08_scheduled_ephemeral/slack.py \
  --exercise --display-name example-owner
```

The live command requires `chat:write`, `SLACK_CHANNEL_ID`, and a unique active
member from `--display-name` or `SLACK_TEST_DISPLAY_NAME`. Ephemeral delivery is
non-persistent and not guaranteed.
