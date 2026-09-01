# Deployment result

This paired scenario reports the outcome of deploying one service revision to
an environment.

## Required meaning

- outcome and severity;
- service and environment;
- deployed revision;
- elapsed duration and completion time;
- one details action.

The canonical fixture is under
[`contracts/test-vectors/scenarios/deployment-result`](../../../../contracts/test-vectors/scenarios/deployment-result).
Reusable construction belongs to
[`application/scenarios/deployment_result.py`](../../src/pyhookkit/application/scenarios/deployment_result.py).

## Provider behavior

Slack renders Block Kit facts and a URL button. Teams renders Adaptive Card
facts and `Action.OpenUrl`. Both providers preserve the same successful outcome
and details URL; payload shape and visual layout intentionally differ.

## Run

From `examples/python`:

```shell
uv run python scenarios/deployment_result/slack.py
uv run python scenarios/deployment_result/teams.py
```

Rendering is the default. Add `--send` only after loading the corresponding
webhook credential and checking the synthetic output.

CI can provide validated runtime values:

```shell
uv run python -m pyhookkit.entrypoints.scenario_cli \
  deployment-result teams \
  --event-id deploy-example-1042 \
  --correlation-id deploy-example-1042 \
  --service bookinfo \
  --deployment-environment staging \
  --revision 9f3a2c1 \
  --duration "2m 18s" \
  --completed-at 2026-08-28T03:15:00Z \
  --deployment-url https://deployments.example.com/runs/1042
```

The integrated scenario creates this notification after Argo CD reports a
healthy successful sync.
