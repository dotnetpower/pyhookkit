# F08: Thread or reply

`threadKey` is provider-neutral. A persistence adapter must map it to the
Slack parent message timestamp before rendering a reply.

Incoming Webhooks return `ok`, not a message timestamp. Obtain and retain the
parent `ts` from a Web API post response or another authorized Slack API
source. The committed channel and timestamp are synthetic.

Teams Workflow webhooks cannot target a parent channel message. The Teams
example therefore renders an explicit degraded-capability card containing the
requested `threadKey`; `--send` posts that card as a new channel message. A true
Teams reply requires a separately authenticated bot or Microsoft Graph adapter
and suitable channel-message permission.

```shell
python fundamentals/08_thread_or_reply/slack.py
python fundamentals/08_thread_or_reply/teams.py
```
