# Fundamentals

Fundamentals progress from Hello World through basic notifications, rich cards,
mentions, links, images, routing, threading, mutation, and retry behavior.

Each capability contains sibling `slack.py` and `teams.py` scripts.

| ID | Capability | Slack | Microsoft Teams |
|---|---|---|---|
| F00 | [Raw HTTP request](00_http_request/README.md) | Standard-library Incoming Webhook POST | Standard-library Workflow POST |
| F01 | [Hello World](01_hello_world/README.md) | Incoming Webhook text | Minimal Adaptive Card |
| F02 | [Basic notification](02_basic_notification/README.md) | Block Kit title, body, severity, timestamp | Adaptive Card title, body, severity, timestamp |
| F03 | [Rich card](03_rich_card/README.md) | Ordered facts and context | Fact panel and context |
| F04 | [Mention](04_mention/README.md) | Native user and user-group mentions | Native user mention; group expansion requires Graph configuration |
| F05 | [Link and action](05_link_and_action/README.md) | HTTPS link button | `Action.OpenUrl` |
| F06 | [Image](06_image/README.md) | External image with alt text | Adaptive Card image with alt text |
| F07 | [Routing](07_routing/README.md) | Logical route to environment secret | Logical route to Workflow environment secret |
| F08 | [Thread or reply](08_thread_or_reply/README.md) | Known parent timestamp required | Explicit new-message fallback; advanced adapter required |
| F09 | [Update and delete](09_update_and_delete/README.md) | Web API payloads; bot token required | Explicit unsupported notice; advanced adapter required |
| F10 | [Error and retry](10_error_and_retry/README.md) | Redacted result, Retry-After, bounded backoff | Redacted result, Retry-After, bounded backoff |

Slack reference implementations and Teams parity siblings are complete.
Provider limitations remain explicit where Workflow webhooks cannot preserve
the requested operation.
