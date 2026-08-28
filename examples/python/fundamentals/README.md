# Fundamentals

Fundamentals progress from Hello World through basic notifications, rich cards,
mentions, links, images, routing, threading, mutation, and retry behavior.

Each capability will contain sibling `slack.py` and `teams.py` scripts.

| ID | Capability | Slack status |
|---|---|---|
| F00 | Raw HTTP request | Standard-library Incoming Webhook POST |
| F01 | Hello World | Incoming Webhook text |
| F02 | Basic notification | Block Kit title, body, severity, timestamp |
| F03 | Rich card | Ordered facts and context |
| F04 | Mention | User and user-group aliases |
| F05 | Link and action | HTTPS link button |
| F06 | Image | External image with alt text |
| F07 | Routing | Logical route to environment secret |
| F08 | Thread or reply | Known parent timestamp required |
| F09 | Update and delete | Web API payloads; bot token required |
| F10 | Error and retry | Redacted result, Retry-After, bounded backoff |

Slack reference implementations are complete. Teams siblings are added in the
next parity phase after the Slack snapshots and behavior are fixed.
