# Contract tests

Contract tests validate language-neutral fixtures and provider payload shapes.

They load schemas from the repository-level `contracts/` directory, validate
date-time and HTTPS formats, reject unknown fields, and ensure domain objects
serialize within the same limits.

The Logic App definition contract also enforces required routing, secure
trigger/connector data, and explicit `201`, `400`, and `502` responses.

Run them from `examples/python`:

```shell
uv run pytest --no-cov tests/contract
```

Contract fixtures must remain synthetic and provider-neutral. The final full
suite enforces repository-wide branch coverage.
