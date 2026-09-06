"""Application boundaries for producer API-key authentication."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


class ProducerAuthenticationError(ValueError):
    """Producer credentials are missing, invalid, expired, or revoked."""


class ProducerAuthorizationError(ValueError):
    """An authenticated producer is not allowed to submit to a route or target."""


@dataclass(frozen=True, slots=True)
class AuthenticatedProducer:
    """Producer identity with optional route or target restrictions."""

    producer: str
    route: str | None = None
    target_id: str | None = None

    def authorize(self, *, route: str, target_id: str | None) -> None:
        """Reject a submission outside this credential's configured scope."""
        if self.route is not None and self.route != route:
            raise ProducerAuthorizationError("producer credential does not allow route")
        if self.target_id is not None and self.target_id != target_id:
            raise ProducerAuthorizationError(
                "producer credential does not allow target"
            )


class ProducerCredentialVerifier(Protocol):
    """Authenticate an HTTP producer request without exposing its credential."""

    def authenticate(self, headers: Mapping[str, str]) -> AuthenticatedProducer: ...
