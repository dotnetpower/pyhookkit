"""GitHub, GitLab, and Azure DevOps native webhook adapter tests."""

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest

from pyhookkit.adapters.inbound.azure_devops_webhook import (
    parse_azure_devops_webhook,
)
from pyhookkit.adapters.inbound.github_webhook import parse_github_webhook
from pyhookkit.adapters.inbound.gitlab_webhook import parse_gitlab_webhook
from pyhookkit.adapters.inbound.provider_webhook import (
    ProviderWebhookAuthenticationError,
    ProviderWebhookPayloadError,
)
from pyhookkit.domain.notification import Severity

_ROUTE = "release-notifications"
_GITHUB_SECRET = "synthetic-github-webhook-secret"
_GITLAB_KEY = b"synthetic-gitlab-signing-key-32b"
_GITLAB_TOKEN = "whsec_" + base64.b64encode(_GITLAB_KEY).decode()
_NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)


def _github_headers(body: bytes, event: str) -> dict[str, str]:
    signature = hmac.new(_GITHUB_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return {
        "x-hub-signature-256": f"sha256={signature}",
        "x-github-delivery": "11111111-1111-4111-8111-111111111111",
        "x-github-event": event,
    }


def _gitlab_headers(body: bytes, event: str) -> dict[str, str]:
    message_id = "22222222-2222-4222-8222-222222222222"
    timestamp = str(int(_NOW.timestamp()))
    message = f"{message_id}.{timestamp}.".encode() + body
    signature = base64.b64encode(
        hmac.new(_GITLAB_KEY, message, hashlib.sha256).digest()
    ).decode()
    return {
        "webhook-id": message_id,
        "webhook-timestamp": timestamp,
        "webhook-signature": f"v1,old v1,{signature}",
        "x-gitlab-event": event,
    }


def test_github_workflow_and_deployment_events() -> None:
    workflow_body = json.dumps(
        {
            "workflow_run": {
                "name": "Build",
                "conclusion": "success",
                "html_url": "https://github.example/runs/1",
            },
            "repository": {"full_name": "example/service"},
        }
    ).encode()
    deployment_body = json.dumps(
        {
            "deployment_status": {
                "state": "failure",
                "target_url": "https://github.example/deployments/1",
            },
            "deployment": {"environment": "staging"},
            "repository": {"full_name": "example/service"},
        }
    ).encode()

    workflow = parse_github_webhook(
        workflow_body,
        _github_headers(workflow_body, "workflow_run"),
        secret=_GITHUB_SECRET,
        route=_ROUTE,
    )
    deployment = parse_github_webhook(
        deployment_body,
        _github_headers(deployment_body, "deployment_status"),
        secret=_GITHUB_SECRET,
        route=_ROUTE,
    )

    assert workflow.notification.severity is Severity.SUCCESS
    assert workflow.notification.event_id.startswith("github-")
    assert deployment.notification.severity is Severity.ERROR
    assert deployment.notification.facts[1].value == "staging"


def test_github_ping_becomes_connection_notification() -> None:
    body = json.dumps(
        {
            "zen": "Synthetic connectivity check",
            "repository": {
                "full_name": "example/service",
                "html_url": "https://github.example/example/service",
            },
        }
    ).encode()

    parsed = parse_github_webhook(
        body,
        _github_headers(body, "ping"),
        secret=_GITHUB_SECRET,
        route=_ROUTE,
    )

    assert parsed.notification.title == "GitHub Webhook connection verified"
    assert parsed.notification.facts[1].value == "ping"


def test_github_pull_request_and_rejections() -> None:
    body = json.dumps(
        {
            "action": "review_requested",
            "pull_request": {
                "title": "Release candidate",
                "html_url": "https://github.example/pull/1",
            },
            "repository": {"full_name": "example/service"},
        }
    ).encode()
    parsed = parse_github_webhook(
        body,
        _github_headers(body, "pull_request"),
        secret=_GITHUB_SECRET,
        route="change-approvals",
    )
    assert parsed.notification.severity is Severity.WARNING

    with pytest.raises(ProviderWebhookAuthenticationError, match="signature"):
        parse_github_webhook(
            body,
            {**_github_headers(body, "pull_request"), "x-hub-signature-256": "bad"},
            secret=_GITHUB_SECRET,
            route=_ROUTE,
        )
    with pytest.raises(ProviderWebhookPayloadError, match="unsupported"):
        parse_github_webhook(
            body,
            _github_headers(body, "push"),
            secret=_GITHUB_SECRET,
            route=_ROUTE,
        )

    unsupported_action = json.dumps(
        {
            "action": "closed",
            "pull_request": {"title": "Closed"},
            "repository": {"full_name": "example/service"},
        }
    ).encode()
    with pytest.raises(ProviderWebhookPayloadError, match="action"):
        parse_github_webhook(
            unsupported_action,
            _github_headers(unsupported_action, "pull_request"),
            secret=_GITHUB_SECRET,
            route=_ROUTE,
        )


@pytest.mark.parametrize(
    "body, message",
    [
        (b"{", "JSON"),
        (b"[]", "object"),
        (json.dumps({"workflow_run": {}, "repository": {}}).encode(), "field"),
    ],
)
def test_github_rejects_malformed_payloads(body: bytes, message: str) -> None:
    with pytest.raises(ProviderWebhookPayloadError, match=message):
        parse_github_webhook(
            body,
            _github_headers(body, "workflow_run"),
            secret=_GITHUB_SECRET,
            route=_ROUTE,
        )


def test_gitlab_pipeline_deployment_and_merge_request_events() -> None:
    pipeline_body = json.dumps(
        {
            "object_attributes": {
                "status": "success",
                "url": "https://gitlab.example/pipelines/1",
            },
            "project": {"path_with_namespace": "example/service"},
        }
    ).encode()
    deployment_body = json.dumps(
        {
            "status": "failed",
            "environment": "staging",
            "deployable_url": "https://gitlab.example/jobs/1",
            "project": {"path_with_namespace": "example/service"},
        }
    ).encode()
    merge_body = json.dumps(
        {
            "object_attributes": {
                "action": "approved",
                "title": "Release candidate",
                "url": "https://gitlab.example/merge_requests/1",
            },
            "project": {"path_with_namespace": "example/service"},
        }
    ).encode()

    pipeline = parse_gitlab_webhook(
        pipeline_body,
        _gitlab_headers(pipeline_body, "Pipeline Hook"),
        signing_token=_GITLAB_TOKEN,
        route=_ROUTE,
        clock=lambda: _NOW,
    )
    deployment = parse_gitlab_webhook(
        deployment_body,
        _gitlab_headers(deployment_body, "Deployment Hook"),
        signing_token=_GITLAB_TOKEN,
        route=_ROUTE,
        clock=lambda: _NOW,
    )
    merge_request = parse_gitlab_webhook(
        merge_body,
        _gitlab_headers(merge_body, "Merge Request Hook"),
        signing_token=_GITLAB_TOKEN,
        route="change-approvals",
        clock=lambda: _NOW,
    )

    assert pipeline.notification.severity is Severity.SUCCESS
    assert deployment.notification.severity is Severity.ERROR
    assert merge_request.notification.severity is Severity.SUCCESS


def test_gitlab_rejects_stale_or_invalid_signatures() -> None:
    body = json.dumps(
        {
            "object_attributes": {"status": "success"},
            "project": {"path_with_namespace": "example/service"},
        }
    ).encode()
    headers = _gitlab_headers(body, "Pipeline Hook")

    with pytest.raises(ProviderWebhookAuthenticationError, match="stale"):
        parse_gitlab_webhook(
            body,
            headers,
            signing_token=_GITLAB_TOKEN,
            route=_ROUTE,
            clock=lambda: _NOW + timedelta(minutes=6),
        )
    with pytest.raises(ProviderWebhookAuthenticationError, match="invalid"):
        parse_gitlab_webhook(
            body,
            {**headers, "webhook-signature": "v1,bad"},
            signing_token=_GITLAB_TOKEN,
            route=_ROUTE,
            clock=lambda: _NOW,
        )
    with pytest.raises(ProviderWebhookAuthenticationError, match="token"):
        parse_gitlab_webhook(
            body,
            headers,
            signing_token="legacy-secret",
            route=_ROUTE,
            clock=lambda: _NOW,
        )

    with pytest.raises(ProviderWebhookAuthenticationError, match="missing"):
        parse_gitlab_webhook(
            body,
            {},
            signing_token=_GITLAB_TOKEN,
            route=_ROUTE,
            clock=lambda: _NOW,
        )
    with pytest.raises(ProviderWebhookAuthenticationError, match="timestamp"):
        parse_gitlab_webhook(
            body,
            {**headers, "webhook-timestamp": "invalid"},
            signing_token=_GITLAB_TOKEN,
            route=_ROUTE,
            clock=lambda: _NOW,
        )
    with pytest.raises(ProviderWebhookAuthenticationError, match="token"):
        parse_gitlab_webhook(
            body,
            headers,
            signing_token="whsec_invalid!",
            route=_ROUTE,
            clock=lambda: _NOW,
        )
    with pytest.raises(ProviderWebhookAuthenticationError, match="token"):
        parse_gitlab_webhook(
            body,
            headers,
            signing_token="whsec_" + base64.b64encode(b"short").decode(),
            route=_ROUTE,
            clock=lambda: _NOW,
        )


@pytest.mark.parametrize(
    "body, event, message",
    [
        (b"{", "Pipeline Hook", "JSON"),
        (b"[]", "Pipeline Hook", "object"),
        (json.dumps({"object_attributes": {}}).encode(), "Pipeline Hook", "field"),
        (
            json.dumps(
                {
                    "object_attributes": {"action": "close"},
                    "project": {"path_with_namespace": "example/service"},
                }
            ).encode(),
            "Merge Request Hook",
            "action",
        ),
    ],
)
def test_gitlab_rejects_malformed_payloads(
    body: bytes,
    event: str,
    message: str,
) -> None:
    with pytest.raises(ProviderWebhookPayloadError, match=message):
        parse_gitlab_webhook(
            body,
            _gitlab_headers(body, event),
            signing_token=_GITLAB_TOKEN,
            route=_ROUTE,
            clock=lambda: _NOW,
        )


def test_azure_devops_build_and_release_events() -> None:
    authorization = (
        "Basic " + base64.b64encode(b"pyhookkit:synthetic-password").decode()
    )
    headers = {"authorization": authorization}
    build_body = json.dumps(
        {
            "id": "33333333-3333-4333-8333-333333333333",
            "eventType": "build.complete",
            "resource": {
                "buildNumber": "20260906.1",
                "result": "succeeded",
                "status": "completed",
                "_links": {"web": {"href": "https://dev.azure.com/example/build/1"}},
            },
        }
    ).encode()
    release_body = json.dumps(
        {
            "id": "44444444-4444-4444-8444-444444444444",
            "eventType": "ms.vss-release.deployment-completed-event",
            "resource": {
                "deployment": {"deploymentStatus": "failed"},
                "environment": {"name": "staging"},
                "release": {
                    "name": "Release-1",
                    "_links": {
                        "web": {"href": "https://dev.azure.com/example/release/1"}
                    },
                },
            },
        }
    ).encode()

    build = parse_azure_devops_webhook(
        build_body,
        headers,
        username="pyhookkit",
        password="synthetic-password",
        route=_ROUTE,
    )
    release = parse_azure_devops_webhook(
        release_body,
        headers,
        username="pyhookkit",
        password="synthetic-password",
        route=_ROUTE,
    )

    assert build.notification.severity is Severity.SUCCESS
    assert release.notification.severity is Severity.ERROR

    with pytest.raises(ProviderWebhookAuthenticationError, match="credentials"):
        parse_azure_devops_webhook(
            build_body,
            {"authorization": "Basic bad"},
            username="pyhookkit",
            password="synthetic-password",
            route=_ROUTE,
        )
    wrong = "Basic " + base64.b64encode(b"pyhookkit:wrong").decode()
    with pytest.raises(ProviderWebhookAuthenticationError, match="credentials"):
        parse_azure_devops_webhook(
            build_body,
            {"authorization": wrong},
            username="pyhookkit",
            password="synthetic-password",
            route=_ROUTE,
        )
    with pytest.raises(ProviderWebhookPayloadError, match="unsupported"):
        unsupported = json.dumps({"id": "1", "eventType": "git.push"}).encode()
        parse_azure_devops_webhook(
            unsupported,
            headers,
            username="pyhookkit",
            password="synthetic-password",
            route=_ROUTE,
        )


@pytest.mark.parametrize(
    "body, message",
    [
        (b"{", "JSON"),
        (b"[]", "object"),
        (
            json.dumps({"id": "1", "eventType": "build.complete"}).encode(),
            "field",
        ),
        (
            json.dumps(
                {
                    "id": "1",
                    "eventType": "build.complete",
                    "resource": {},
                }
            ).encode(),
            "field",
        ),
    ],
)
def test_azure_devops_rejects_malformed_payloads(body: bytes, message: str) -> None:
    authorization = (
        "Basic " + base64.b64encode(b"pyhookkit:synthetic-password").decode()
    )
    with pytest.raises(ProviderWebhookPayloadError, match=message):
        parse_azure_devops_webhook(
            body,
            {"authorization": authorization},
            username="pyhookkit",
            password="synthetic-password",
            route=_ROUTE,
        )
