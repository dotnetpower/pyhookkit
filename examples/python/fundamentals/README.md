# Fundamentals

Fundamentals progress from Hello World through basic notifications, rich cards,
mentions, links, images, routing, threading, mutation, and retry behavior.

Each capability will contain sibling `slack.py` and `teams.py` scripts.

| ID | Capability | Slack | Microsoft Teams |
|---|---|---|---|
| F00 | Raw HTTP request | Standard-library Incoming Webhook POST | Standard-library Workflow POST |
| F01 | Hello World | Incoming Webhook text | Minimal Adaptive Card |
| F02 | Basic notification | Block Kit title, body, severity, timestamp | Adaptive Card title, body, severity, timestamp |
| F03 | Rich card | Ordered facts and context | Fact panel and context |
| F04 | Mention | Native user and user-group mentions | Native user mention; group expansion requires Graph configuration |
| F05 | Link and action | HTTPS link button | `Action.OpenUrl` |
| F06 | Image | External image with alt text | Adaptive Card image with alt text |
| F07 | Routing | Logical route to environment secret | Logical route to Workflow environment secret |
| F08 | Thread or reply | Known parent timestamp required | Explicit new-message fallback; advanced adapter required |
| F09 | Update and delete | Web API payloads; bot token required | Explicit unsupported notice; advanced adapter required |
| F10 | Error and retry | Redacted result, Retry-After, bounded backoff | Redacted result, Retry-After, bounded backoff |

Slack reference implementations and Teams parity siblings are complete.
Provider limitations remain explicit where Workflow webhooks cannot preserve
the requested operation.
