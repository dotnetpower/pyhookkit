"""Slack delivery classification and retry tests."""

from collections.abc import Callable

import httpx
import pytest

import pyhookkit.adapters.outbound.slack.http_transport as transport_module
from pyhookkit.adapters.outbound.slack.http_transport import (
    HttpxSlackHttpTransport,
    SlackHttpResponse,
    SlackHttpTimeouts,
    SlackTransportError,
)
from pyhookkit.adapters.outbound.slack.response_classifier import (
    classify_slack_response,
)
from pyhookkit.adapters.outbound.slack.retry_policy import SlackRetryPolicy
from pyhookkit.adapters.outbound.slack.webhook_destination import (
    SlackWebhookDestination,
)
from pyhookkit.adapters.outbound.slack.webhook_url import SlackWebhookUrl
from pyhookkit.domain.delivery import DeliveryErrorKind, DeliveryState
from pyhookkit.json_types import JsonObject


class StubTransport:
    """Return deterministic responses without network access."""

    def __init__(
        self,
        outcomes: list[SlackHttpResponse | SlackTransportError],
    ) -> None:
        self._outcomes = outcomes
        self.calls = 0

    def post(
        self,
        url: str,
        payload: JsonObject,
        timeouts: SlackHttpTimeouts,
    ) -> SlackHttpResponse:
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, SlackTransportError):
            raise outcome
        return outcome


def _response(
    status_code: int,
    *,
    body: str = "error",
    headers: dict[str, str] | None = None,
) -> SlackHttpResponse:
    return SlackHttpResponse(status_code, headers or {}, body)


def _destination(
    transport: StubTransport,
    *,
    delays: list[float] | None = None,
    policy: SlackRetryPolicy | None = None,
) -> SlackWebhookDestination:
    recorded_delays = [] if delays is None else delays
    return SlackWebhookDestination(
        SlackWebhookUrl("https://hooks.slack.com/services/example"),
        transport=transport,
        retry_policy=policy,
        sleep=recorded_delays.append,
        jitter=lambda: 0.5,
    )


def test_successful_delivery_returns_redacted_result() -> None:
    transport = StubTransport([_response(200, body="ok")])

    result = _destination(transport).send({"text": "Synthetic message"})

    assert result.state is DeliveryState.SUCCEEDED
    assert result.attempts == 1
    assert result.error is None


def test_rate_limit_prioritizes_retry_after() -> None:
    delays: list[float] = []
    transport = StubTransport(
        [
            _response(429, headers={"Retry-After": "2"}),
            _response(200, body="ok"),
        ]
    )

    result = _destination(transport, delays=delays).send({"text": "Synthetic"})

    assert result.state is DeliveryState.SUCCEEDED
    assert result.attempts == 2
    assert delays == [2.0]


def test_transient_provider_error_uses_exponential_backoff() -> None:
    delays: list[float] = []
    transport = StubTransport(
        [
            _response(500),
            _response(503),
            _response(200, body="ok"),
        ]
    )

    result = _destination(transport, delays=delays).send({"text": "Synthetic"})

    assert result.state is DeliveryState.SUCCEEDED
    assert delays == [0.5, 1.0]


def test_transport_failure_stops_at_attempt_limit() -> None:
    marker = "sensitive transport detail"
    transport = StubTransport(
        [
            SlackTransportError(marker),
            SlackTransportError(marker),
            SlackTransportError(marker),
        ]
    )

    result = _destination(transport).send({"text": "sensitive payload"})

    assert result.state is DeliveryState.FAILED
    assert result.attempts == 3
    assert result.error is not None
    assert result.error.kind is DeliveryErrorKind.TRANSPORT
    assert marker not in repr(result)
    assert "sensitive payload" not in repr(result)


@pytest.mark.parametrize(
    ("status_code", "body", "expected_kind"),
    [
        (400, "invalid_payload", DeliveryErrorKind.INVALID_PAYLOAD),
        (401, "invalid_token", DeliveryErrorKind.AUTHENTICATION),
        (403, "action_prohibited", DeliveryErrorKind.PERMISSION),
        (404, "channel_not_found", DeliveryErrorKind.PERMANENT_PROVIDER),
        (200, "unexpected", DeliveryErrorKind.PERMANENT_PROVIDER),
    ],
)
def test_permanent_errors_are_not_retried(
    status_code: int,
    body: str,
    expected_kind: DeliveryErrorKind,
) -> None:
    transport = StubTransport([_response(status_code, body=body)])

    result = _destination(transport).send({"text": "Synthetic"})

    assert transport.calls == 1
    assert result.error is not None
    assert result.error.kind is expected_kind
    assert result.error.retryable is False


@pytest.mark.parametrize("retry_after", ["invalid", "-1"])
def test_invalid_retry_after_falls_back_to_policy(retry_after: str) -> None:
    classification = classify_slack_response(
        _response(429, headers={"retry-after": retry_after})
    )

    assert classification.retry_after_seconds is None


def test_retry_policy_bounds_retry_after_and_jitter() -> None:
    policy = SlackRetryPolicy(max_delay_seconds=4)

    assert policy.delay(1, retry_after_seconds=10, jitter=0.5) == 10
    assert policy.delay(1, retry_after_seconds=121, jitter=0.5) == 120
    assert policy.delay(5, retry_after_seconds=None, jitter=1) == 4


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SlackRetryPolicy(max_attempts=0),
        lambda: SlackRetryPolicy(base_delay_seconds=0),
        lambda: SlackRetryPolicy(base_delay_seconds=2, max_delay_seconds=1),
        lambda: SlackRetryPolicy().delay(0, None, 0.5),
        lambda: SlackRetryPolicy().delay(1, None, -0.1),
    ],
)
def test_retry_policy_rejects_invalid_configuration(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ValueError):
        factory()


def test_http_timeouts_must_be_positive() -> None:
    with pytest.raises(ValueError, match="timeout"):
        SlackHttpTimeouts(read_seconds=0)


def test_httpx_transport_returns_only_classification_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def post(
        url: str,
        *,
        json: object,
        timeout: httpx.Timeout,
    ) -> httpx.Response:
        assert url == "https://hooks.slack.com/services/example"
        assert json == {"text": "Synthetic"}
        assert timeout.connect == 5
        return httpx.Response(200, headers={"Example": "value"}, text="ok")

    monkeypatch.setattr(transport_module.httpx, "post", post)

    response = HttpxSlackHttpTransport().post(
        "https://hooks.slack.com/services/example",
        {"text": "Synthetic"},
        SlackHttpTimeouts(),
    )

    assert response.status_code == 200
    assert response.headers["example"] == "value"
    assert response.body == "ok"


def test_httpx_transport_redacts_underlying_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def post(
        url: str,
        *,
        json: object,
        timeout: httpx.Timeout,
    ) -> httpx.Response:
        raise httpx.ConnectError("sensitive webhook details")

    monkeypatch.setattr(transport_module.httpx, "post", post)

    with pytest.raises(SlackTransportError) as captured:
        HttpxSlackHttpTransport().post(
            "https://hooks.slack.com/services/example",
            {"text": "Synthetic"},
            SlackHttpTimeouts(),
        )

    assert str(captured.value) == "Slack webhook transport failed"
    assert captured.value.__cause__ is None
