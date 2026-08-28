---
name: add-notification-example
description: Add a Slack-first, Teams-paired notification capability or scenario with shared fixtures, parity tests, and explicit provider differences.
---

# Add a paired notification example

Use this skill when adding a fundamental notification capability or a detailed
scenario. Do not use it for provider-only maintenance that does not change
observable notification behavior.

## Inputs

Before editing, identify:

- the capability or scenario name;
- the required semantic fields and user action;
- whether each provider supports the behavior directly, approximately, or not
  at all;
- the minimum permissions and delivery adapter needed.

Use only synthetic values. Never copy customer payloads, names, routes,
identifiers, URLs, or credentials.

## Procedure

1. **Define the canonical case**
   - Add one provider-neutral fixture under
     `contracts/test-vectors/fundamentals/<name>/` or
     `contracts/test-vectors/scenarios/<name>/`.
   - Validate it against the canonical notification schema.
   - State the semantic fields that parity must preserve.

2. **Implement Slack reference behavior**
   - Add or extend one responsibility-specific Slack renderer or destination.
   - Add the thin `slack.py` example beside the scenario README.
   - Freeze the expected Slack payload and test error behavior.

3. **Implement Teams parity behavior**
   - Add or extend the corresponding Teams renderer or destination.
   - Add the sibling `teams.py` example using the same canonical input.
   - Freeze the expected Teams payload and test error behavior.

4. **Assert semantic parity**
   - Compare required meaning, not JSON shape or visual pixels.
   - Check title, body, severity, facts, mentions, links, and core actions when
     applicable.
   - Record equivalent, degraded, advanced-adapter, and unsupported behavior
     explicitly. Never silently drop a requested capability.

5. **Document and verify**
   - Explain provider differences, permissions, bootstrap steps, and limits in
     the example README.
   - Run targeted format, lint, strict type, contract, unit, parity, and secret
     checks.

## Expected layout

```text
examples/python/fundamentals/03_rich_card/
├── README.md
├── example_notification.py
├── slack.py
└── teams.py

contracts/test-vectors/fundamentals/rich-card/
├── notification.json
├── slack.expected.json
└── teams.expected.json
```

Provider-specific reusable code belongs under:

```text
src/pyhookkit/adapters/outbound/
├── slack/
└── teams/
```

Do not duplicate rendering or delivery logic in executable example files.

## Completion checklist

- The canonical fixture passes schema validation.
- Slack reference tests pass before Teams parity is accepted.
- Both examples consume the same canonical case.
- Required semantic fields survive both renderers.
- Differences are explicit and documented.
- No provider type leaks into domain or application code.
- No real secret, route, identity, or customer data is committed.
