# Examples

The repository currently provides a Python 3.12 reference implementation under
[`python/`](python/README.md).

Examples are executable documentation:

- paired fundamentals introduce one provider-neutral capability;
- paired scenarios compose complete operational notifications;
- Slack operations demonstrate provider-only Web API and inbound protocols;
- Teams Adaptive Cards demonstrate provider-only presentation patterns.

Executable files stay thin. Reusable behavior belongs in the package under
`python/src/pyhookkit`, while provider-neutral fixtures belong under
`../contracts/test-vectors`.

All examples render or dry-run by default. Network activity requires an
explicit command flag and runtime credentials outside the repository.
