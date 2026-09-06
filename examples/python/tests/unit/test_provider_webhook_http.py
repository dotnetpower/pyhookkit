"""Provider-native webhook HTTP ingestion tests."""

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from pathlib import Path

from pyhookkit.adapters.inbound.provider_webhook_http import (
    ProviderWebhookHttpApplication,
)
from pyhookkit.adapters.outbound.sqlite_inbound_integrations import (
    SqliteInboundIntegrationStore,
)
from pyhookkit.adapters.outbound.sqlite_route_store import (
    SqliteRouteStore,
    StoredDestination,
)
from pyhookkit.application.notification_router import NotificationRouter
from pyhookkit.domain.delivery import DeliveryResult, DeliveryState
from pyhookkit.domain.notification import CanonicalNotification
from pyhookkit.ports.inbound_integrations import InboundIntegration

_SECRET = "synthetic-github-webhook-secret"
_GITLAB_KEY = b"synthetic-gitlab-signing-key-32b"
_GITLAB_TOKEN = "whsec_" + base64.b64encode(_GITLAB_KEY).decode()


class SuccessfulDelivery:
    def deliver(
        self,
        target_id: str,
        notification: CanonicalNotification,
    ) -> DeliveryResult:
        del target_id, notification
        return DeliveryResult(DeliveryState.SUCCEEDED, attempts=1)


def _application(tmp_path: Path) -> ProviderWebhookHttpApplication:
    database = tmp_path / "router.sqlite3"
    routes = SqliteRouteStore(database)
    routes.configure_destination(
        StoredDestination(
            "teams-release",
            "release-notifications",
            "teams-workflow",
            "TEAMS_WORKFLOW_URL",
            (
                "https://teams.cloud.microsoft/l/channel/"
                "19%3Aexample%40thread.tacv2/Release"
                "?groupId=11111111-1111-4111-8111-111111111111"
                "&tenantId=22222222-2222-4222-8222-222222222222"
            ),
            True,
        )
    )
    integrations = SqliteInboundIntegrationStore(database)
    integrations.configure(
        InboundIntegration(
            "github-release",
            "github",
            "github",
            "GITHUB_WEBHOOK_SECRET",
            "release-notifications",
            "teams-release",
            None,
            True,
        )
    )
    integrations.configure(
        InboundIntegration(
            "gitlab-release",
            "gitlab",
            "gitlab",
            "GITLAB_WEBHOOK_SIGNING_TOKEN",
            "release-notifications",
            "teams-release",
            None,
            True,
        )
    )
    integrations.configure(
        InboundIntegration(
            "azure-build",
            "azure-devops",
            "azure-devops",
            "AZURE_DEVOPS_WEBHOOK_PASSWORD",
            "release-notifications",
            "teams-release",
            "pyhookkit",
            True,
        )
    )
    integrations.configure(
        InboundIntegration(
            "github-unavailable",
            "github",
            "github",
            "MISSING_SECRET",
            "release-notifications",
            None,
            None,
            True,
        )
    )
    return ProviderWebhookHttpApplication(
        NotificationRouter(routes, SuccessfulDelivery()),
        integrations,
        {
            "GITHUB_WEBHOOK_SECRET": _SECRET,
            "GITLAB_WEBHOOK_SIGNING_TOKEN": _GITLAB_TOKEN,
            "AZURE_DEVOPS_WEBHOOK_PASSWORD": "synthetic-password",
        },
    )


def _request(body: bytes) -> tuple[dict[str, str], bytes]:
    signature = hmac.new(_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return (
        {
            "content-type": "application/json",
            "x-hub-signature-256": f"sha256={signature}",
            "x-github-delivery": "11111111-1111-4111-8111-111111111111",
            "x-github-event": "workflow_run",
        },
        body,
    )


def test_provider_webhook_queues_only_configured_target(tmp_path: Path) -> None:
    application = _application(tmp_path)
    body = json.dumps(
        {
            "workflow_run": {
                "name": "Build",
                "conclusion": "success",
                "html_url": "https://github.example/runs/1",
            },
            "repository": {"full_name": "example/service"},
        }
    ).encode()
    headers, request_body = _request(body)

    accepted = application.handle(
        "POST",
        "/v1/inbound/github/github-release",
        headers,
        request_body,
    )
    duplicate = application.handle(
        "POST",
        "/v1/inbound/github/github-release",
        headers,
        request_body,
    )

    assert accepted.status_code == 202
    assert accepted.body["targetId"] == "teams-release"
    assert duplicate.status_code == 202
    assert duplicate.body["duplicate"] is True


def test_provider_webhook_rejects_invalid_boundary_requests(tmp_path: Path) -> None:
    application = _application(tmp_path)
    body = b"{}"
    headers, _ = _request(body)

    assert application.handles("POST", "/v1/inbound/github/github-release") is True
    assert application.handle("GET", "/missing", {}, b"").status_code == 404
    assert (
        application.handle(
            "POST",
            "/v1/inbound/github/missing",
            {"content-type": "application/json"},
            body,
        ).status_code
        == 404
    )
    assert (
        application.handle(
            "POST",
            "/v1/inbound/github/github-release",
            {**headers, "content-type": "text/plain"},
            body,
        ).status_code
        == 415
    )
    assert (
        application.handle(
            "POST",
            "/v1/inbound/github/github-release",
            {**headers, "x-hub-signature-256": "bad"},
            body,
        ).status_code
        == 401
    )
    assert (
        application.handle(
            "POST",
            "/v1/inbound/github/github-unavailable",
            {"content-type": "application/json"},
            body,
        ).status_code
        == 503
    )
    assert (
        application.handle(
            "POST",
            "/v1/inbound/github/github-release",
            headers,
            body,
        ).status_code
        == 422
    )
    application.max_body_bytes = 1
    assert (
        application.handle(
            "POST",
            "/v1/inbound/github/github-release",
            headers,
            body,
        ).status_code
        == 413
    )


def test_provider_webhook_accepts_gitlab_and_azure_devops(tmp_path: Path) -> None:
    application = _application(tmp_path)
    gitlab_body = json.dumps(
        {
            "object_attributes": {
                "status": "success",
                "url": "https://gitlab.example/pipelines/1",
            },
            "project": {"path_with_namespace": "example/service"},
        }
    ).encode()
    message_id = "22222222-2222-4222-8222-222222222222"
    timestamp = str(int(datetime.now(UTC).timestamp()))
    message = f"{message_id}.{timestamp}.".encode() + gitlab_body
    signature = base64.b64encode(
        hmac.new(_GITLAB_KEY, message, hashlib.sha256).digest()
    ).decode()
    gitlab = application.handle(
        "POST",
        "/v1/inbound/gitlab/gitlab-release",
        {
            "content-type": "application/json",
            "webhook-id": message_id,
            "webhook-timestamp": timestamp,
            "webhook-signature": f"v1,{signature}",
            "x-gitlab-event": "Pipeline Hook",
        },
        gitlab_body,
    )

    azure_body = json.dumps(
        {
            "id": "33333333-3333-4333-8333-333333333333",
            "eventType": "build.complete",
            "resource": {
                "buildNumber": "20260906.1",
                "result": "succeeded",
                "status": "completed",
            },
        }
    ).encode()
    azure = application.handle(
        "POST",
        "/v1/inbound/azure-devops/azure-build",
        {
            "content-type": "application/json",
            "authorization": "Basic "
            + base64.b64encode(b"pyhookkit:synthetic-password").decode(),
        },
        azure_body,
    )

    assert gitlab.status_code == 202
    assert gitlab.body["integrationId"] == "gitlab-release"
    assert azure.status_code == 202
    assert azure.body["integrationId"] == "azure-build"
