# Python tests

The Python test suite is divided by boundary:

- [`unit/`](unit/README.md): domain, adapter, entrypoint, and parity behavior;
- [`contract/`](contract/README.md): language-neutral schemas and committed
  vectors;
- [`integration/`](integration/README.md): composed local boundaries that do
  not require live provider credentials.

Run all configured quality gates from `examples/python`:

```shell
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -q
```

Pytest measures branch coverage for the `pyhookkit` package and requires at
least 90 percent total coverage.
