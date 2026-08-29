"""Microsoft Teams response classification and retry tests."""

from collections.abc import Callable

import httpx
import pytest

from pyhookkit.adapters.outbound.teams.http_delivery import (
    classify_teams_response,
)
from pyhookkit.adapters.outbound.teams.retry_policy import TeamsRetryPolicy
from pyhookkit.adapters.outbound.teams.workflow_destination import (
    TeamsWorkflowDestination,
)
from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.domain.delivery import DeliveryErrorKind, DeliveryState

_URL = (
    "https://default-example.environment.api.powerplatform.com/"
    "powerautomate/automations/direct/workflows/example/triggers/manual/paths/"
    "invoke?api-version=1&sig=synthetic"
)


class StubPost:
    def __init__(
        self,
        outcomes: list[httpx.Response | httpx.TransportError],
    ) -> None:
        self._outcomes = outcomes
        self.calls = 0

    def __call__(self, *_args: object, **_kwargs: object) -> httpx.Response:
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, httpx.TransportError):
            raise outcome
        return outcome


def _destination(
    post: StubPost,
    *,
    delays: list[float] | None = None,
) -> TeamsWorkflowDestination:
    recorded_delays = [] if delays is None else delays
    return TeamsWorkflowDestination(
        TeamsWorkflowUrl(_URL),
        post=post,
        sleep=recorded_delays.append,
        jitter=lambda: 0.5,
    )


def test_rate_limit_prioritizes_retry_after() -> None:
    delays: list[float] = []
    post = StubPost(
        [
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(202),
        ]
    )

    result = _destination(post, delays=delays).send({"type": "message"})

    assert result.state is DeliveryState.SUCCEEDED
    assert result.attempts == 2
    assert delays == [2.0]


def test_transient_failure_uses_bounded_backoff() -> None:
    delays: list[float] = []
    post = StubPost(
        [
            httpx.Response(500),
            httpx.Response(503),
            httpx.Response(202),
        ]
    )

    result = _destination(post, delays=delays).send({"type": "message"})

    assert result.state is DeliveryState.SUCCEEDED
    assert result.attempts == 3
    assert delays == [0.5, 1.0]


def test_transport_failure_stops_at_attempt_limit_and_is_redacted() -> None:
    marker = "sensitive transport detail"
    post = StubPost(
        [
            httpx.ConnectError(marker),
            httpx.ConnectError(marker),
            httpx.ConnectError(marker),
        ]
    )

    result = _destination(post).send({"text": "sensitive payload"})

    assert result.state is DeliveryState.FAILED
    assert result.attempts == 3
    assert result.error is not None
    assert result.error.kind is DeliveryErrorKind.TRANSPORT
    assert marker not in repr(result)
    assert "sensitive payload" not in repr(result)


@pytest.mark.parametrize("retry_after", ["invalid", "-1"])
def test_invalid_retry_after_falls_back_to_policy(retry_after: str) -> None:
    classification = classify_teams_response(
        httpx.Response(429, headers={"Retry-After": retry_after})
    )

    assert classification.retry_after_seconds is None


def test_retry_policy_bounds_retry_after_and_jitter() -> None:
    policy = TeamsRetryPolicy(max_delay_seconds=4)

    assert policy.delay(1, retry_after_seconds=10, jitter=0.5) == 10
    assert policy.delay(1, retry_after_seconds=121, jitter=0.5) == 120
    assert policy.delay(5, retry_after_seconds=None, jitter=1) == 4


@pytest.mark.parametrize(
    "factory",
    [
        lambda: TeamsRetryPolicy(max_attempts=0),
        lambda: TeamsRetryPolicy(base_delay_seconds=0),
        lambda: TeamsRetryPolicy(base_delay_seconds=2, max_delay_seconds=1),
        lambda: TeamsRetryPolicy().delay(0, None, 0.5),
        lambda: TeamsRetryPolicy().delay(1, None, -0.1),
    ],
)
def test_retry_policy_rejects_invalid_configuration(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ValueError):
        factory()
