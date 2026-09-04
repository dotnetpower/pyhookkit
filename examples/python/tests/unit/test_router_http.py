"""Authenticated central router HTTP boundary tests."""

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from pyhookkit.adapters.inbound.router_http import (
    ProducerAuthenticator,
    RouterHttpApplication,
    RouterRequestHandler,
)
from pyhookkit.adapters.outbound.sqlite_route_store import (
    SqliteRouteStore,
    StoredDestination,
)
from pyhookkit.application.notification_router import NotificationRouter
from pyhookkit.domain.delivery import DeliveryResult, DeliveryState
from pyhookkit.domain.notification import CanonicalNotification

_TOKEN = "synthetic-router-token"
_HEADERS = {
    "authorization": f"Bearer {_TOKEN}",
    "x-pyhookkit-producer": "gitlab",
    "content-type": "application/json",
}
_PAYLOAD = {
    "schemaVersion": "1.0",
    "eventId": "router-http-001",
    "route": "release-notifications",
    "body": "Deployment completed",
    "severity": "success",
}


class SuccessfulDelivery:
    def deliver(
        self,
        target_id: str,
        notification: CanonicalNotification,
    ) -> DeliveryResult:
        del target_id, notification
        return DeliveryResult(DeliveryState.SUCCEEDED, attempts=1)


def _application(tmp_path: Path) -> tuple[RouterHttpApplication, NotificationRouter]:
    store = SqliteRouteStore(tmp_path / "router.sqlite3")
    store.configure_destination(
        StoredDestination(
            target_id="slack-staging",
            route="release-notifications",
            provider="slack",
            endpoint_environment_variable="SLACK_WEBHOOK_URL",
            channel_link=None,
            enabled=True,
        )
    )
    router = NotificationRouter(store, SuccessfulDelivery())
    return (
        RouterHttpApplication(
            router,
            ProducerAuthenticator({"gitlab": _TOKEN, "argocd": "argocd-token-1234"}),
        ),
        router,
    )


def test_http_accepts_duplicate_and_returns_delivery_status(tmp_path: Path) -> None:
    application, router = _application(tmp_path)
    body = json.dumps(_PAYLOAD).encode()

    accepted = application.handle("POST", "/v1/notifications", _HEADERS, body)
    duplicate = application.handle("POST", "/v1/notifications", _HEADERS, body)

    assert accepted.status_code == 202
    assert accepted.body["duplicate"] is False
    assert duplicate.status_code == 202
    assert duplicate.body["duplicate"] is True
    notification_id = accepted.body["notificationId"]
    assert isinstance(notification_id, str)

    assert router.deliver_next() is True
    status = application.handle(
        "GET",
        f"/v1/notifications/{notification_id}",
        _HEADERS,
    )

    assert status.status_code == 200
    assert status.body["state"] == "delivered"


def test_http_authentication_and_ownership_are_isolated(tmp_path: Path) -> None:
    application, _ = _application(tmp_path)
    body = json.dumps(_PAYLOAD).encode()

    unauthorized = application.handle(
        "POST",
        "/v1/notifications",
        {"content-type": "application/json"},
        body,
    )
    accepted = application.handle("POST", "/v1/notifications", _HEADERS, body)
    notification_id = accepted.body["notificationId"]
    assert isinstance(notification_id, str)
    other_headers = {
        "authorization": "Bearer argocd-token-1234",
        "x-pyhookkit-producer": "argocd",
    }
    hidden = application.handle(
        "GET",
        f"/v1/notifications/{notification_id}",
        other_headers,
    )

    assert unauthorized.status_code == 401
    assert hidden.status_code == 404


def test_http_rejects_invalid_input_without_enqueuing(tmp_path: Path) -> None:
    application, _ = _application(tmp_path)

    invalid_json = application.handle(
        "POST",
        "/v1/notifications",
        _HEADERS,
        b"{",
    )
    invalid_contract = application.handle(
        "POST",
        "/v1/notifications",
        _HEADERS,
        json.dumps({**_PAYLOAD, "provider": "teams"}).encode(),
    )
    wrong_type = application.handle(
        "POST",
        "/v1/notifications",
        {**_HEADERS, "content-type": "text/plain"},
        json.dumps(_PAYLOAD).encode(),
    )
    too_large = RouterHttpApplication(
        _application(tmp_path)[1],
        ProducerAuthenticator({"gitlab": _TOKEN}),
        max_body_bytes=2,
    ).handle("POST", "/v1/notifications", _HEADERS, b"{}!")

    assert invalid_json.status_code == 400
    assert invalid_contract.status_code == 422
    assert wrong_type.status_code == 415
    assert too_large.status_code == 413


def test_http_exposes_unauthenticated_health_only(tmp_path: Path) -> None:
    application, _ = _application(tmp_path)

    health = application.handle("GET", "/healthz", {})
    missing = application.handle("GET", "/unknown", _HEADERS)

    assert health == type(health)(200, {"status": "ok"})
    assert missing.status_code == 404


def test_standard_library_http_handler_serves_application(tmp_path: Path) -> None:
    application, _ = _application(tmp_path)
    RouterRequestHandler.application = application
    server = ThreadingHTTPServer(("127.0.0.1", 0), RouterRequestHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    try:
        connection.request("GET", "/healthz")
        health = connection.getresponse()
        assert health.status == 200
        assert json.loads(health.read()) == {"status": "ok"}

        body = json.dumps(_PAYLOAD)
        connection.request(
            "POST",
            "/v1/notifications",
            body=body,
            headers={
                "Authorization": f"Bearer {_TOKEN}",
                "X-PyHookKit-Producer": "gitlab",
                "Content-Type": "application/json",
            },
        )
        accepted = connection.getresponse()
        assert accepted.status == 202
        assert json.loads(accepted.read())["state"] == "queued"
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize(
    "content_length, expected_status", [("bad", 400), ("70000", 413)]
)
def test_http_handler_rejects_invalid_length(
    tmp_path: Path,
    content_length: str,
    expected_status: int,
) -> None:
    application, _ = _application(tmp_path)
    RouterRequestHandler.application = application
    server = ThreadingHTTPServer(("127.0.0.1", 0), RouterRequestHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    try:
        connection.putrequest("POST", "/v1/notifications")
        connection.putheader("Content-Length", content_length)
        connection.endheaders()
        response = connection.getresponse()
        assert response.status == expected_status
        response.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
