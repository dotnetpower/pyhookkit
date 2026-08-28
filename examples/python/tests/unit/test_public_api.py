"""PyHookKit package root API tests."""

import pyhookkit


def test_domain_types_are_available_from_package_root() -> None:
    notification = pyhookkit.CanonicalNotification(
        schema_version="1.0",
        event_id="example-public-api-001",
        route="hello-world",
        body="Hello from PyHookKit.",
        severity=pyhookkit.Severity.INFO,
    )

    assert notification.body == "Hello from PyHookKit."
    assert "CanonicalNotification" in pyhookkit.__all__
