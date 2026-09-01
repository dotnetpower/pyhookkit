# Contracts

This directory owns the language-neutral `notification.schema.json` and
`delivery-result.schema.json` contracts. `test-vectors` contains synthetic
canonical inputs and paired provider outputs.

Schema changes must remain explicit and versioned. A language implementation
must not redefine the contract independently. Domain boundary and collection
limits are tested against the schemas.

## Contents

- [`notification.schema.json`](notification.schema.json): canonical
  notification input;
- [`delivery-result.schema.json`](delivery-result.schema.json):
  provider-neutral delivery outcome;
- [`test-vectors/`](test-vectors/README.md): canonical inputs and frozen
  provider renderings.

Validate schema and vector changes with:

```shell
cd examples/python
uv run pytest --no-cov tests/contract
```

Provider identifiers, payload-only fields, destination URLs, and credentials do
not belong in canonical schemas or inputs. Run the complete suite before
finishing a change so the repository-wide coverage threshold is enforced.
