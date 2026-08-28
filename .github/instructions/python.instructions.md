---
description: Python-specific design and quality rules
applyTo: 'examples/python/**/*.py'
---

- Use Python 3.12 syntax and complete parameter and return annotations.
- Use frozen, slotted dataclasses for domain value objects when appropriate.
- Use tuples or read-only mappings at immutable domain boundaries.
- Raise narrow validation errors with actionable messages.
- Keep imports aligned with the inward dependency rule; domain and ports must
  not import adapters or entrypoints.
- Avoid `Any`, unchecked casts, mutable default arguments, and catch-all
  exceptions.
- Keep tests behavior-focused and include both successful and rejected paths.
