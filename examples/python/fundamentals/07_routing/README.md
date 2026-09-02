# F07: Routing

The canonical `platform-alerts` route resolves to `SLACK_WEBHOOK_URL` or
`TEAMS_WORKFLOW_URL` and the exact allowlisted
`TEAMS_WORKFLOW_CHANNEL_LINK` at the provider entrypoint. Neither the domain nor
application code receives a provider destination.

Load `.env`, then validate the route without printing the credential:

```shell
uv run python fundamentals/07_routing/slack.py --check-route
uv run python fundamentals/07_routing/teams.py --check-route
```
