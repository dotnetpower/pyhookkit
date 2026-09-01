# Approval request

This paired scenario asks one identified reviewer to approve a bounded release
request.

## Required meaning

- request identifier and subject;
- requester;
- deadline;
- logical approver alias;
- one review action.

The canonical fixture is under
[`contracts/test-vectors/scenarios/approval-request`](../../../../contracts/test-vectors/scenarios/approval-request).
Reusable construction belongs to
[`application/scenarios/approval_request.py`](../../src/pyhookkit/application/scenarios/approval_request.py).

## Provider behavior

Slack maps the approver alias to a native member ID. Teams maps it to a native
mention entity and matching display name. Both require explicit provider-owned
identity configuration for a live dynamic send.

The review button is navigation, not an in-card approval. In the integrated
Bookinfo scenario it opens the GitHub Actions run; the protected GitHub
Environment remains the approval system of record.

## Run

From `examples/python`:

```shell
uv run python scenarios/approval_request/slack.py
uv run python scenarios/approval_request/teams.py
```

The committed render uses synthetic identities. For a live automation send,
use `scenario_cli` and provide either the Slack user ID or both the Teams user
identifier and display name. Never put provider identity values in the
canonical fixture.

The complete GitHub approval sequence and client capture are in the
[integrated Bookinfo scenario](../../../../docs/integrated-bookinfo-scenario.md#scenario-1-deployment-approval).
