# Unit tests

Unit tests cover domain invariants and one adapter responsibility at a time.

They also execute thin example entrypoints, retry classification, identity
resolution, provider payload limits, redaction, and Slack/Teams semantic parity.

Run one focused module for fast feedback:

```shell
uv run pytest --no-cov tests/unit/test_notification_automation.py
```

Targeted execution disables coverage because the threshold applies to the whole
package. Use the complete suite for the final verification result.
