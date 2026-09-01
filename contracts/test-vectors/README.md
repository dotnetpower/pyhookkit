# Contract test vectors

Test vectors freeze the provider-neutral input and provider-specific output for
observable notification behavior.

- [`fundamentals/`](fundamentals/README.md) covers one capability at a time.
- [`scenarios/`](scenarios/README.md) covers complete operational messages.

Each case contains `notification.json` and the expected Slack and Teams
renderings. A provider-specific file is added only when that provider has an
observable output for the case.

Fixtures must validate against `../notification.schema.json`, use synthetic
values, and preserve semantic meaning rather than identical provider JSON.
Update the paired expected outputs and parity tests whenever a canonical case
changes.
