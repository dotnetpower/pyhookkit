# Contracts

This directory owns the language-neutral `notification.schema.json` and
`delivery-result.schema.json` contracts. `test-vectors` contains synthetic
canonical inputs and paired provider outputs.

Schema changes must remain explicit and versioned. A language implementation
must not redefine the contract independently. Domain boundary and collection
limits are tested against the schemas.
