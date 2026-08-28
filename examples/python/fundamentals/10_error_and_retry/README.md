# F10: Error and retry

The Slack destination classifies validation, authentication, permission,
rate-limit, transient provider, and transport failures without retaining the
webhook URL, request payload, or provider response body.

It prioritizes `Retry-After`; otherwise it uses bounded exponential backoff
with jitter. Validation and permanent `4xx` failures are not retried.

Load `.env` and deliberately send the synthetic test message:

```shell
uv run python fundamentals/10_error_and_retry/slack.py --send
```
