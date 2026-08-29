# F09: Update and delete

Incoming Webhooks cannot update or delete a posted message. These payloads
target Slack Web API methods `chat.update` and `chat.delete` and require a bot
token with `chat:write`, the channel ID, and the original message timestamp.

The bot can mutate messages it authored; this example does not send mutation
requests.

Teams Workflow webhooks cannot update or delete an existing channel message.
The Teams example renders this limitation explicitly alongside the canonical
replacement content. If `--send` is used, it creates a new limitation notice;
it does not pretend to mutate an existing message. Actual Teams mutation
requires a bot or Microsoft Graph adapter, a persisted message identifier, and
appropriate channel-message permission.

```shell
python fundamentals/09_update_and_delete/slack.py
python fundamentals/09_update_and_delete/teams.py
```
