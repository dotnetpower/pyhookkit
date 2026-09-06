"""Provider-native webhook parsing result and boundary errors."""

from dataclasses import dataclass

from pyhookkit.domain.notification import CanonicalNotification


class ProviderWebhookAuthenticationError(ValueError):
    """A provider-native webhook could not be authenticated."""


class ProviderWebhookPayloadError(ValueError):
    """A provider-native webhook payload is invalid or unsupported."""


@dataclass(frozen=True, slots=True)
class ParsedProviderWebhook:
    """Authenticated provider event transformed into one canonical notification."""

    notification: CanonicalNotification
    delivery_id: str
