"""Microsoft Teams Workflow callback URL validation."""

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True, repr=False)
class TeamsWorkflowUrl:
    """A validated Power Platform Workflow callback URL."""

    value: str

    def __post_init__(self) -> None:
        parsed = urlsplit(self.value)
        hostname = parsed.hostname
        if (
            parsed.scheme != "https"
            or hostname is None
            or not hostname.endswith(".environment.api.powerplatform.com")
            or "/workflows/" not in parsed.path
            or not parsed.query
        ):
            raise ValueError("invalid Teams Workflow callback URL")

    def __repr__(self) -> str:
        return "TeamsWorkflowUrl(value=<redacted>)"
