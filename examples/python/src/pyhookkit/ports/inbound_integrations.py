"""Application boundaries for provider-native inbound integrations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class InboundIntegration:
    """Non-secret provider webhook routing and authentication configuration."""

    integration_id: str
    provider: str
    producer: str
    secret_environment_variable: str
    route: str
    target_id: str | None
    username: str | None
    enabled: bool
    created_at: str | None = None
    last_received_at: str | None = None


class InboundIntegrationStore(Protocol):
    """Persist and inspect provider-native inbound integration metadata."""

    def configure(self, integration: InboundIntegration) -> None: ...

    def integration(self, integration_id: str) -> InboundIntegration | None: ...

    def integrations(self) -> tuple[InboundIntegration, ...]: ...

    def mark_received(self, integration_id: str, received_at: datetime) -> None: ...
