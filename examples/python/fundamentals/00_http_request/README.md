# F00: Raw HTTP request

This bootstrap example sends `Hello, world!` without importing `pyhookkit` or
installing third-party packages. The Slack and Teams scripts share
`example_message.py` and use only Python's standard library.

The message body is the same semantic input as the canonical
`contracts/test-vectors/fundamentals/hello-world/notification.json` fixture.
Slack receives a text payload, while Teams receives the equivalent text in an
Adaptive Card. Their JSON shapes are intentionally provider-specific.

From `examples/python`, render the requests without credentials:

```shell
python fundamentals/00_http_request/slack.py
python fundamentals/00_http_request/teams.py
```

To send deliberately, load the repository `.env` and select a provider:

```shell
python fundamentals/00_http_request/slack.py --send
python fundamentals/00_http_request/teams.py --send
python fundamentals/00_http_request/teams.py --send-logic-app
```

Slack requires `SLACK_WEBHOOK_URL` for an Incoming Webhook. Teams requires
`TEAMS_WORKFLOW_URL` for the shared Workflow HTTP POST callback and
`TEAMS_WORKFLOW_CHANNEL_LINK` for its exact allowlisted destination. Logic App delivery uses
`TEAMS_LOGIC_APP_URL`, `TEAMS_LOGIC_APP_TEAM_ID`, and
`TEAMS_LOGIC_APP_CHANNEL_ID`. All destinations must be HTTPS URLs. The scripts
report only the HTTP status and never print the destination URL or provider
response body.
