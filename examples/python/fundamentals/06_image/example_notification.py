"""Canonical input for the image example."""

from pyhookkit.domain.notification import (
    CanonicalNotification,
    Image,
    Severity,
)

ASSET_FILENAME = "samples/recipe/assets/recipe_image.png"
_SYNTHETIC_IMAGE_URL = f"https://assets.pyhookkit.example/{ASSET_FILENAME}"


def build_notification(
    image_url: str = _SYNTHETIC_IMAGE_URL,
) -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-image-001",
        route="platform-alerts",
        title="Sample image",
        body="A publicly hosted sample image is attached.",
        severity=Severity.INFO,
        image=Image(
            image_url,
            "Glazed chicken with broccoli from the Microsoft Adaptive Cards "
            "recipe sample",
        ),
    )
