"""Slack Incoming Webhook URL validation."""

from dataclasses import dataclass
from urllib.parse import urlsplit

_ALLOWED_HOSTS = frozenset({"hooks.slack.com", "hooks.slack-gov.com"})


@dataclass(frozen=True, slots=True)
class SlackWebhookUrl:
    """A validated Slack-owned Incoming Webhook URL."""

    value: str

    def __post_init__(self) -> None:
        parsed = urlsplit(self.value)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in _ALLOWED_HOSTS
            or not parsed.path.startswith("/services/")
        ):
            raise ValueError("invalid Slack Incoming Webhook URL")
