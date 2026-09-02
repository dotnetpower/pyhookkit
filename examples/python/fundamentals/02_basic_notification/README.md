# F02: Basic notification

Adds title, severity color, and source timestamp to paired Slack and Teams
messages. Slack uses a Block Kit attachment and retains top-level `text` as an
accessible fallback. Teams uses an Adaptive Card 1.4 attachment and retains the
same title and body in `fallbackText` and `speak`. The basic Teams layout omits
the optional presentation hero so the card contains no image.

From `examples/python`, render either provider without credentials:

```shell
python fundamentals/02_basic_notification/slack.py
python fundamentals/02_basic_notification/teams.py
```

Add `--send` to deliberately deliver through `SLACK_WEBHOOK_URL` or
`TEAMS_WORKFLOW_URL` and `TEAMS_WORKFLOW_CHANNEL_LINK`. Teams Workflow delivery
requires no Graph permission.
