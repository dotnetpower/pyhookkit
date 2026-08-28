"""Azure Logic App callback URL validation."""

from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit


@dataclass(frozen=True, slots=True, repr=False)
class TeamsLogicAppUrl:
    """A validated Azure Logic App HTTP trigger callback URL."""

    value: str

    def __post_init__(self) -> None:
        parsed = urlsplit(self.value)
        hostname = parsed.hostname
        query = parse_qs(parsed.query)
        if (
            parsed.scheme != "https"
            or hostname is None
            or not hostname.endswith(".logic.azure.com")
            or "/triggers/" not in parsed.path
            or not parsed.path.endswith("/invoke")
            or "sig" not in query
        ):
            raise ValueError("invalid Teams Logic App callback URL")

    def __repr__(self) -> str:
        return "TeamsLogicAppUrl(value=<redacted>)"
