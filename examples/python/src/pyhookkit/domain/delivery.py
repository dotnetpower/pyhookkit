"""Provider-neutral delivery outcomes."""

from dataclasses import dataclass
from enum import StrEnum


class DeliveryState(StrEnum):
    """Terminal state of a delivery attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DeliveryErrorKind(StrEnum):
    """Stable error categories shared across provider adapters."""

    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMITED = "rate_limited"
    INVALID_PAYLOAD = "invalid_payload"
    TRANSIENT_PROVIDER = "transient_provider"
    TRANSPORT = "transport"
    PERMANENT_PROVIDER = "permanent_provider"


@dataclass(frozen=True, slots=True)
class DeliveryError:
    """A redacted delivery failure."""

    kind: DeliveryErrorKind
    retryable: bool
    status_code: int | None = None


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """The result of sending one provider payload."""

    state: DeliveryState
    attempts: int
    error: DeliveryError | None = None

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("delivery attempts must be positive")
        if self.state is DeliveryState.SUCCEEDED and self.error is not None:
            raise ValueError("successful delivery cannot contain an error")
        if self.state is DeliveryState.FAILED and self.error is None:
            raise ValueError("failed delivery must contain an error")
