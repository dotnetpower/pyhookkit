"""Authenticated router administration dashboard tests."""

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from pyhookkit.adapters.inbound.admin_http import (
    AdminAuthenticator,
    RouterAdminHttpApplication,
    RouterAdminRequestHandler,
)
from pyhookkit.json_types import JsonObject

_TOKEN = "synthetic-admin-token-123456"
_HEADERS = {"authorization": f"Bearer {_TOKEN}"}


class StubAdminController:
    def __init__(self) -> None:
        self.added: tuple[str, str] | None = None
        self.tested: str | None = None
        self.revoked: str | None = None
        self.integration: JsonObject | None = None

    def destinations(self) -> tuple[JsonObject, ...]:
        return (
            {
                "targetId": "teams-general-example",
                "route": "release-notifications",
                "provider": "teams-workflow",
                "channelName": "General",
                "membershipType": "private",
                "enabled": True,
                "webhookUrl": (
                    "https://notify.example.test/v1/destinations/"
                    "teams-general-example/notifications"
                ),
            },
        )

    def notifications(self) -> tuple[JsonObject, ...]:
        return (
            {
                "notificationId": "11111111-1111-4111-8111-111111111111",
                "producer": "gitlab",
                "eventId": "release-001",
                "createdAt": "2026-01-01T00:00:00+00:00",
                "state": "delivered",
                "deliveries": [],
            },
        )

    def add_teams_channel(self, *, route: str, channel_link: str) -> JsonObject:
        if route == "invalid":
            raise ValueError("route is invalid")
        self.added = (route, channel_link)
        return {
            "targetId": "teams-general-example",
            "route": route,
            "channelName": "General",
            "membership": "already_present",
            "state": "configured",
        }

    def test_destination(self, target_id: str) -> JsonObject:
        self.tested = target_id
        if target_id == "teams-failing":
            return {"targetId": target_id, "state": "failed", "attempts": 1}
        return {
            "targetId": target_id,
            "channelName": "General",
            "state": "succeeded",
            "attempts": 1,
        }

    def api_keys(self) -> tuple[JsonObject, ...]:
        return (
            {
                "keyId": "abcdef123456",
                "producer": "github",
                "state": "active",
            },
        )

    def issue_api_key(
        self,
        *,
        producer: str,
        route: str | None,
        target_id: str | None,
    ) -> JsonObject:
        return {
            "keyId": "abcdef123456",
            "producer": producer,
            "route": route,
            "targetId": target_id,
            "apiKey": "phk_abcdef123456_synthetic-issued-api-key-value-000000",
        }

    def revoke_api_key(self, key_id: str) -> bool:
        self.revoked = key_id
        return key_id == "abcdef123456"

    def integrations(self) -> tuple[JsonObject, ...]:
        return (
            {
                "integrationId": "github-release",
                "provider": "github",
                "producer": "github",
            },
        )

    def add_integration(self, value: JsonObject) -> JsonObject:
        self.integration = value
        return {**value, "state": "configured"}


def _application() -> tuple[RouterAdminHttpApplication, StubAdminController]:
    controller = StubAdminController()
    return (
        RouterAdminHttpApplication(controller, AdminAuthenticator(_TOKEN)),
        controller,
    )


def test_dashboard_is_public_but_data_requires_admin_token() -> None:
    application, _ = _application()

    dashboard = application.handle("GET", "/admin", {})
    unauthorized = application.handle("GET", "/admin/api/destinations", {})
    destinations = application.handle(
        "GET",
        "/admin/api/destinations",
        _HEADERS,
    )
    notifications = application.handle(
        "GET",
        "/admin/api/notifications",
        _HEADERS,
    )

    assert dashboard.status_code == 200
    assert dashboard.content_type == "text/html; charset=utf-8"
    assert b"PyHookKit Router" in dashboard.body
    assert _TOKEN.encode() not in dashboard.body
    assert (
        dashboard.body.index(b'id="channel-link"')
        < dashboard.body.index(b'id="channel-name"')
        < dashboard.body.index(b'id="route"')
    )
    assert b'id="channel-name" readonly' in dashboard.body
    assert b"resetAddForm" in dashboard.body
    assert "웹훅 연동".encode() in dashboard.body
    assert b'"<your-api-key>"' in dashboard.body
    assert b"Authorization: Bearer ${apiKey}" in dashboard.body
    assert b"\"  --data-binary @- <<'JSON'\"" in dashboard.body
    assert b'id="webhook-sample"' in dashboard.body
    assert b'id="webhook-url" readonly' in dashboard.body
    assert b'id="webhook-api-key" type="password"' in dashboard.body
    assert b'id="generate-webhook-key"' in dashboard.body
    assert "phk_ API 키".encode() in dashboard.body
    assert b'id="webhook-language"' in dashboard.body
    assert 'aria-label="샘플 코드 복사"'.encode() in dashboard.body
    assert 'aria-label="새 API 키 생성"'.encode() in dashboard.body
    assert 'aria-label="API 키 표시"'.encode() in dashboard.body
    assert 'aria-label="API 키 복사"'.encode() in dashboard.body
    assert 'aria-label="필수 헤더 복사"'.encode() in dashboard.body
    assert 'aria-label="Payload 복사"'.encode() in dashboard.body
    assert b'item.membershipType === "private"' in dashboard.body
    assert 'aria-label", isPrivate ? "비공개 채널"'.encode() in dashboard.body
    assert b'id="webhook-producer"' in dashboard.body
    assert b'value="gitlab"' in dashboard.body
    assert b"X-PyHookKit-Producer: ${producer}" in dashboard.body
    assert b"Authorization: Bearer &lt;your-api-key&gt;" in dashboard.body
    assert b'request("/admin/api/api-keys"' in dashboard.body
    assert b'id="integrations"' in dashboard.body
    assert b'id="api-keys"' in dashboard.body
    assert b'id="integration-dialog"' in dashboard.body
    assert b'closeOnBackdrop(byId("add-dialog"), closeAddDialog)' in dashboard.body
    assert b'closeOnBackdrop(byId("webhook-dialog"), closeWebhookDialog)' in (
        dashboard.body
    )
    assert "원문은 한 번만 표시".encode() in dashboard.body
    assert b"item.webhookUrl" in dashboard.body
    assert "채널 링크의 테넌트가 현재 TeamsNotifyApp 테넌트와 다릅니다.".encode() in (
        dashboard.body
    )
    assert unauthorized.status_code == 401
    assert json.loads(destinations.body)["items"][0]["channelName"] == "General"
    assert json.loads(notifications.body)["items"][0]["state"] == "delivered"


def test_admin_authenticator_rejects_short_token() -> None:
    with pytest.raises(ValueError, match="at least 24"):
        AdminAuthenticator("too-short")


def test_admin_api_adds_one_validated_channel() -> None:
    application, controller = _application()
    channel_link = (
        "https://teams.cloud.microsoft/l/channel/"
        "19%3Aexample%40thread.tacv2/General"
        "?groupId=11111111-1111-4111-8111-111111111111"
        "&tenantId=22222222-2222-4222-8222-222222222222"
    )

    response = application.handle(
        "POST",
        "/admin/api/destinations",
        {**_HEADERS, "content-type": "application/json"},
        json.dumps(
            {
                "route": "release-notifications",
                "channelLink": channel_link,
            }
        ).encode(),
    )

    assert response.status_code == 201
    assert json.loads(response.body)["state"] == "configured"
    assert controller.added == ("release-notifications", channel_link)


def test_admin_api_sends_test_to_selected_destination() -> None:
    application, controller = _application()

    succeeded = application.handle(
        "POST",
        "/admin/api/destinations/teams-general-example/test",
        _HEADERS,
    )
    failed = application.handle(
        "POST",
        "/admin/api/destinations/teams-failing/test",
        _HEADERS,
    )
    unauthorized = application.handle(
        "POST",
        "/admin/api/destinations/teams-general-example/test",
        {},
    )

    assert succeeded.status_code == 200
    assert json.loads(succeeded.body)["state"] == "succeeded"
    assert failed.status_code == 502
    assert unauthorized.status_code == 401
    assert controller.tested == "teams-failing"


def test_admin_api_manages_api_keys_and_inbound_integrations() -> None:
    application, controller = _application()

    keys = application.handle("GET", "/admin/api/api-keys", _HEADERS)
    issued = application.handle(
        "POST",
        "/admin/api/api-keys",
        {**_HEADERS, "content-type": "application/json"},
        json.dumps(
            {"producer": "github", "targetId": "teams-general-example"}
        ).encode(),
    )
    revoked = application.handle(
        "DELETE",
        "/admin/api/api-keys/abcdef123456",
        _HEADERS,
    )
    missing = application.handle(
        "DELETE",
        "/admin/api/api-keys/000000000000",
        _HEADERS,
    )
    integrations = application.handle(
        "GET",
        "/admin/api/integrations",
        _HEADERS,
    )
    configured = application.handle(
        "POST",
        "/admin/api/integrations",
        {**_HEADERS, "content-type": "application/json"},
        json.dumps(
            {
                "integrationId": "github-release",
                "provider": "github",
                "producer": "github",
                "secretEnvironmentVariable": "GITHUB_WEBHOOK_SECRET",
                "route": "release-notifications",
            }
        ).encode(),
    )

    assert json.loads(keys.body)["items"][0]["producer"] == "github"
    assert issued.status_code == 201
    assert json.loads(issued.body)["apiKey"].startswith("phk_")
    assert revoked.status_code == 200
    assert controller.revoked == "000000000000"
    assert missing.status_code == 404
    assert json.loads(integrations.body)["items"][0]["provider"] == "github"
    assert configured.status_code == 201
    assert controller.integration is not None


def test_admin_api_rejects_unsupported_or_malformed_input() -> None:
    application, controller = _application()

    wrong_type = application.handle(
        "POST",
        "/admin/api/destinations",
        {**_HEADERS, "content-type": "text/plain"},
        b"{}",
    )
    extra_field = application.handle(
        "POST",
        "/admin/api/destinations",
        {**_HEADERS, "content-type": "application/json"},
        json.dumps(
            {"route": "release", "channelLink": "https://example.test", "secret": "no"}
        ).encode(),
    )
    invalid_json = application.handle(
        "POST",
        "/admin/api/destinations",
        {**_HEADERS, "content-type": "application/json"},
        b"{",
    )
    not_an_object = application.handle(
        "POST",
        "/admin/api/destinations",
        {**_HEADERS, "content-type": "application/json"},
        b"[]",
    )
    wrong_field_types = application.handle(
        "POST",
        "/admin/api/destinations",
        {**_HEADERS, "content-type": "application/json"},
        json.dumps({"route": 1, "channelLink": False}).encode(),
    )
    controller_error = application.handle(
        "POST",
        "/admin/api/destinations",
        {**_HEADERS, "content-type": "application/json"},
        json.dumps(
            {"route": "invalid", "channelLink": "https://example.test"}
        ).encode(),
    )
    too_large = application.handle(
        "POST",
        "/admin/api/destinations",
        {**_HEADERS, "content-type": "application/json"},
        b"x" * (application.max_body_bytes + 1),
    )
    missing_route = application.handle("GET", "/missing", _HEADERS)
    wrong_method = application.handle(
        "POST",
        "/admin/api/notifications",
        _HEADERS,
        b"",
    )

    assert wrong_type.status_code == 415
    assert extra_field.status_code == 422
    assert invalid_json.status_code == 400
    assert not_an_object.status_code == 422
    assert wrong_field_types.status_code == 422
    assert controller_error.status_code == 422
    assert too_large.status_code == 413
    assert missing_route.status_code == 404
    assert wrong_method.status_code == 404
    assert controller.added is None


def test_standard_library_handler_serves_dashboard() -> None:
    application, _ = _application()
    RouterAdminRequestHandler.application = application
    server = ThreadingHTTPServer(("127.0.0.1", 0), RouterAdminRequestHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    try:
        connection.request("GET", "/admin")
        dashboard = connection.getresponse()
        assert dashboard.status == 200
        assert dashboard.getheader("X-Frame-Options") == "DENY"
        assert b"PyHookKit Router" in dashboard.read()

        connection.request(
            "GET",
            "/admin/api/destinations",
            headers={"Authorization": f"Bearer {_TOKEN}"},
        )
        destinations = connection.getresponse()
        assert destinations.status == 200
        assert json.loads(destinations.read())["items"][0]["targetId"] == (
            "teams-general-example"
        )

        for content_length, expected_status in (
            ("bad", 400),
            ("-1", 400),
            ("20000", 413),
        ):
            connection.putrequest("POST", "/admin/api/destinations")
            connection.putheader("Content-Length", content_length)
            connection.endheaders()
            rejected = connection.getresponse()
            assert rejected.status == expected_status
            rejected.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
