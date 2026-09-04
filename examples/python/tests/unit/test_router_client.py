"""Central notification router client tests."""

from collections.abc import Callable

import httpx
import pytest

from pyhookkit.adapters.outbound.router_client import (
    NotificationRouterClient,
    NotificationRouterToken,
    NotificationRouterUrl,
)

_TOKEN = "synthetic-router-token"


def test_client_submits_with_producer_credential() -> None:
    def post(
        url: str,
        *,
        json: object,
        headers: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        assert url == "http://127.0.0.1:8080/v1/notifications"
        assert json == {"schemaVersion": "1.0"}
        assert headers["Authorization"] == f"Bearer {_TOKEN}"
        assert headers["X-PyHookKit-Producer"] == "gitlab"
        assert timeout == 15.0
        return httpx.Response(
            202,
            json={
                "notificationId": "11111111-1111-4111-8111-111111111111",
                "duplicate": False,
                "state": "queued",
            },
        )

    result = NotificationRouterClient(
        NotificationRouterUrl("http://127.0.0.1:8080"),
        NotificationRouterToken(_TOKEN),
        "gitlab",
        post=post,
    ).submit({"schemaVersion": "1.0"})

    assert result.state == "queued"
    assert result.duplicate is False


def test_client_rejects_non_tls_remote_url_and_failed_response() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        NotificationRouterUrl("http://router.example.com")

    client = NotificationRouterClient(
        NotificationRouterUrl("https://router.example.com"),
        NotificationRouterToken(_TOKEN),
        "argocd",
        post=lambda *_args, **_kwargs: httpx.Response(401),
    )
    with pytest.raises(ValueError, match="HTTP 401"):
        client.submit({"schemaVersion": "1.0"})


@pytest.mark.parametrize(
    "factory",
    [
        lambda: NotificationRouterToken("short"),
        lambda: NotificationRouterClient(
            NotificationRouterUrl("https://router.example.com"),
            NotificationRouterToken(_TOKEN),
            " ",
        ),
        lambda: NotificationRouterClient(
            NotificationRouterUrl("https://router.example.com"),
            NotificationRouterToken(_TOKEN),
            "gitlab",
            timeout_seconds=0,
        ),
    ],
)
def test_client_rejects_invalid_configuration(factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        factory()


def test_client_rejects_malformed_success_response() -> None:
    client = NotificationRouterClient(
        NotificationRouterUrl("https://router.example.com/base/"),
        NotificationRouterToken(_TOKEN),
        "gitlab",
        post=lambda *_args, **_kwargs: httpx.Response(202, json=[]),
    )

    with pytest.raises(ValueError, match="JSON object"):
        client.submit({"schemaVersion": "1.0"})

    missing_fields_client = NotificationRouterClient(
        NotificationRouterUrl("https://router.example.com"),
        NotificationRouterToken(_TOKEN),
        "gitlab",
        post=lambda *_args, **_kwargs: httpx.Response(202, json={}),
    )
    with pytest.raises(ValueError, match="required fields"):
        missing_fields_client.submit({"schemaVersion": "1.0"})
