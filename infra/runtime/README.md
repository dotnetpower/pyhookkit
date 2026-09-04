# Runtime boundaries

Runtime directories reserve deployment-specific composition without changing
the provider-neutral contract:

- [`local/`](local/README.md) defines offline and mock execution;
- [`container/`](container/README.md) defines container secret injection;
- [`azure/`](azure/README.md) defines managed-identity composition.

The local runtime documents the optional SQLite central router. No container or
Azure router deployment is committed yet. The live Bookinfo scenario uses the
explicit assets under
[`../azure/bicep/`](../azure/bicep/README.md) and
[`../gitops/bookinfo/`](../gitops/bookinfo/README.md).

Add a runtime asset only when it has a concrete consumer, validation command,
credential boundary, and removal procedure.
