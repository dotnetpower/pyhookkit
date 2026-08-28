# F08: Thread or reply

`threadKey` is provider-neutral. A persistence adapter must map it to the
Slack parent message timestamp before rendering a reply.

Incoming Webhooks return `ok`, not a message timestamp. Obtain and retain the
parent `ts` from a Web API post response or another authorized Slack API
source. The committed channel and timestamp are synthetic.
