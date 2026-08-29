"""Bounded Microsoft Teams webhook retry timing."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TeamsRetryPolicy:
    """Retry limits and exponential backoff bounds."""

    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0
    max_retry_after_seconds: float = 120.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("maximum attempts must be positive")
        if self.base_delay_seconds <= 0:
            raise ValueError("base retry delay must be positive")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("maximum retry delay must not be less than base delay")
        if self.max_retry_after_seconds < self.max_delay_seconds:
            raise ValueError(
                "maximum Retry-After must not be less than maximum retry delay"
            )

    def delay(
        self,
        completed_attempts: int,
        retry_after_seconds: float | None,
        jitter: float,
    ) -> float:
        if completed_attempts < 1:
            raise ValueError("completed attempts must be positive")
        if not 0 <= jitter <= 1:
            raise ValueError("jitter must be between zero and one")
        if retry_after_seconds is not None:
            return min(retry_after_seconds, self.max_retry_after_seconds)
        exponential = self.base_delay_seconds * 2 ** (completed_attempts - 1)
        jittered = exponential * (0.5 + jitter)
        return min(jittered, self.max_delay_seconds)
