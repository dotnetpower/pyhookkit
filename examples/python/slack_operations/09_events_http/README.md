# O09: Events API HTTP

Runs a localhost HTTP endpoint for Slack URL verification and event callbacks.
It rejects invalid signatures and requests older than five minutes.

```shell
uv run python slack_operations/09_events_http/slack.py
uv run python slack_operations/09_events_http/slack.py --serve --port 3000
```

Serving requires `SLACK_SIGNING_SECRET`. Expose the local endpoint only through
an approved HTTPS development tunnel and never log the raw event body.
