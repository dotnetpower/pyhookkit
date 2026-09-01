# Azure runtime

No general-purpose Azure runtime deployment is committed here yet.

When a concrete runtime is added, it must use managed identity, workload
identity federation, and least-privilege RBAC instead of embedded client
secrets. Its provider destinations must be injected from an approved secret
store and its Bicep modules must include validation and removal steps.

The current AKS example is intentionally explicit under
[`../../azure/bicep/`](../../azure/bicep/README.md).
