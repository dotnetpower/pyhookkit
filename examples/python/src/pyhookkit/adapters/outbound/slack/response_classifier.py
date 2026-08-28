"""Slack webhook response classification."""

from dataclasses import dataclass

from pyhookkit.adapters.outbound.slack.http_transport import SlackHttpResponse
from pyhookkit.domain.delivery import DeliveryError, DeliveryErrorKind


@dataclass(frozen=True, slots=True)
class SlackResponseClassification:
    """Success or a redacted failure with optional retry timing."""

    error: DeliveryError | None
    retry_after_seconds: float | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


def classify_slack_response(
    response: SlackHttpResponse,
) -> SlackResponseClassification:
    if response.status_code == 200 and response.body.strip() == "ok":
        return SlackResponseClassification(error=None)
    if response.status_code == 429:
        return SlackResponseClassification(
            error=DeliveryError(
                kind=DeliveryErrorKind.RATE_LIMITED,
                retryable=True,
                status_code=429,
            ),
            retry_after_seconds=_retry_after(response),
        )
    if 500 <= response.status_code <= 599:
        return SlackResponseClassification(
            error=DeliveryError(
                kind=DeliveryErrorKind.TRANSIENT_PROVIDER,
                retryable=True,
                status_code=response.status_code,
            )
        )

    kind = {
        400: DeliveryErrorKind.INVALID_PAYLOAD,
        401: DeliveryErrorKind.AUTHENTICATION,
        403: DeliveryErrorKind.PERMISSION,
    }.get(response.status_code, DeliveryErrorKind.PERMANENT_PROVIDER)
    return SlackResponseClassification(
        error=DeliveryError(
            kind=kind,
            retryable=False,
            status_code=response.status_code,
        )
    )


def _retry_after(response: SlackHttpResponse) -> float | None:
    value = next(
        (
            header_value
            for header_name, header_value in response.headers.items()
            if header_name.lower() == "retry-after"
        ),
        None,
    )
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None
