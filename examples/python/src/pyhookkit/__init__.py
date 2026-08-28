"""Typed Slack and Teams notification delivery with semantic parity."""

from pyhookkit.domain.delivery import (
    DeliveryError,
    DeliveryErrorKind,
    DeliveryResult,
    DeliveryState,
)
from pyhookkit.domain.notification import (
    CanonicalNotification,
    Fact,
    Image,
    Link,
    Mention,
    MentionKind,
    Severity,
)

__all__ = [
    "CanonicalNotification",
    "DeliveryError",
    "DeliveryErrorKind",
    "DeliveryResult",
    "DeliveryState",
    "Fact",
    "Image",
    "Link",
    "Mention",
    "MentionKind",
    "Severity",
]
