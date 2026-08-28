# F07: Routing

The canonical `platform-alerts` route resolves to the
`SLACK_WEBHOOK_URL` environment variable at the entrypoint. Neither the domain
nor application code receives the webhook URL.

Load `.env`, then validate the route without printing the credential:

```shell
uv run python fundamentals/07_routing/slack.py --check-route
```
