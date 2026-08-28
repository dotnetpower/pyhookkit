# Repository engineering instructions

Build notification parity from one provider-neutral contract. Implement and
test Slack behavior first, then add the semantically equivalent Teams behavior.

## Architecture

- Give each module, class, and function one cohesive responsibility and one
  primary reason to change.
- Keep dependencies pointing inward:
  `entrypoints/adapters -> application/ports -> domain`.
- Keep the domain immutable and free of HTTP, environment, filesystem, cloud,
  provider SDK, and provider payload concerns.
- Keep provider payloads and provider identifiers inside their adapters.
- Assemble concrete adapters only in entrypoints or another explicit
  composition root.
- Prefer small, capability-specific ports over broad service interfaces.
- Do not add generic `utils`, `helpers`, `common`, or `manager` modules. Name a
  module after the domain or technical responsibility it owns.
- Extract an abstraction only when it expresses a stable boundary or removes
  duplication from at least two real consumers.

## Implementation

- Target Python 3.12 and use complete type annotations.
- Prefer immutable value objects and explicit result types.
- Reject invalid input at the boundary with a specific error. Do not silently
  discard unsupported fields or convert failures into success-shaped results.
- Keep functions readable and cohesive; line count alone is not a design goal.
- Never log raw notification payloads, credentials, destination URLs, or
  provider responses that may contain sensitive data.
- Use synthetic aliases, routes, identifiers, URLs, and payloads in committed
  examples and tests.

## Paired examples

- Organize examples by capability or scenario, with `slack.py` and `teams.py`
  as siblings that consume the same canonical input.
- Keep executable examples thin. Reusable behavior belongs under
  `src/pyhookkit`.
- Preserve required semantic fields rather than forcing provider payloads to
  have identical shapes.
- Represent provider differences as explicit capabilities, warnings, or
  unsupported results.

## Verification

- Add focused unit, contract, and parity tests with each behavior change.
- Run Ruff format/check, Pyright strict, pytest with branch coverage of at
  least 90%, schema validation, and relevant IaC validation.
- Test retry classification, redaction, and negative paths when those concerns
  are introduced.

Prefer this:

```python
class SlackMessageRenderer:
    def render(self, notification: CanonicalNotification) -> JsonObject: ...
```

over a broad provider-aware manager:

```python
class NotificationManager:
    def render_and_send(self, provider: str, payload: dict[str, object]) -> object: ...
```
