# Migration

Migration starts only after contract, provider parity, infrastructure, secret
handling, and rollback paths are validated.

## 1. Inventory

Record each producer, destination, message type, owner, credential, volume,
retry expectation, interaction, thread or mutation requirement, and rollback
contact. Do not copy raw customer payloads or credentials into the inventory.

Exit when every live notification has an owner and a canonical scenario or an
explicit unsupported classification.

## 2. Capability mapping

Map required meaning to the canonical contract and classify each provider
behavior as equivalent, degraded, advanced-adapter, or unsupported. Resolve
identity, threading, update, deletion, and sender-attribution differences
before delivery code is changed.

Exit when paired fixtures and negative tests cover the migration scope.

## 3. Shadow dual-send

Render both providers from the same canonical event. Send the new provider only
to a synthetic shadow destination. Compare semantic fields, delivery results,
latency, retry classification, client rendering, and navigation actions.

Exit when no secret or provider response enters logs and the measured error
rate is within the agreed threshold.

## 4. Canary

Move a small set of routes or low-risk producers to the new destination. Keep
the previous destination and credential valid. Monitor rate limits, transient
failures, missing identity mappings, and user acknowledgment behavior.

Exit when the canary remains stable for the agreed observation window.

## 5. Cutover

Change route configuration rather than canonical producers. Preserve event and
correlation IDs so duplicate notifications can be identified. Freeze unrelated
renderer and infrastructure changes during the cutover window.

## 6. Rollback rehearsal

Before retiring the old path, prove that route configuration and secrets can be
restored without code changes. Rehearse rollback with a synthetic event and
record the time to recovery.

Retire old credentials only after the rollback window closes. Remove obsolete
provider IDs, webhook URLs, infrastructure, and ownership assignments from the
approved secret stores.

The [integrated Bookinfo scenario](integrated-bookinfo-scenario.md) is a
disposable rehearsal environment for approval, GitOps promotion, deployment
result, incident, and maintenance paths.
