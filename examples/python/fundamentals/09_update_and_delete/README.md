# F09: Update and delete

Incoming Webhooks cannot update or delete a posted message. These payloads
target Slack Web API methods `chat.update` and `chat.delete` and require a bot
token with `chat:write`, the channel ID, and the original message timestamp.

The bot can mutate messages it authored; this example does not send mutation
requests.
