# F10: Error and retry

The Slack destination classifies validation, authentication, permission,
rate-limit, transient provider, and transport failures without retaining the
webhook URL, request payload, or provider response body.

It prioritizes `Retry-After`; otherwise it uses bounded exponential backoff
with jitter. Validation and permanent `4xx` failures are not retried.

Teams Workflow and Logic App destinations apply the same provider-neutral
classification and bounded retry semantics. Teams accepts any `2xx` response as
success, honors `Retry-After` on `429`, retries transport and `5xx` failures,
and never retains response bodies, payloads, or destination URLs in results.

Load `.env` and deliberately send the synthetic test message:

```shell
uv run python fundamentals/10_error_and_retry/slack.py --send
uv run python fundamentals/10_error_and_retry/teams.py --send
```
