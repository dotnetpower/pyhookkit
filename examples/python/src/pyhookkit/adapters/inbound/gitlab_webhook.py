"""GitLab Standard Webhooks authentication and canonical transformation."""

import base64
import binascii
import hashlib
import hmac
import json
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import cast

from pyhookkit.adapters.inbound.provider_webhook import (
    ParsedProviderWebhook,
    ProviderWebhookAuthenticationError,
    ProviderWebhookPayloadError,
)
from pyhookkit.domain.notification import CanonicalNotification, Fact, Link, Severity

_EVENT_ID = re.compile(r"[^A-Za-z0-9._:-]+")
_SUPPORTED_EVENTS = frozenset(
    {"Pipeline Hook", "Deployment Hook", "Merge Request Hook"}
)


def parse_gitlab_webhook(
    body: bytes,
    headers: Mapping[str, str],
    *,
    signing_token: str,
    route: str,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    tolerance_seconds: int = 300,
) -> ParsedProviderWebhook:
    """Verify a GitLab Standard Webhook and transform a supported event."""
    message_id = headers.get("webhook-id", "").strip()
    timestamp = headers.get("webhook-timestamp", "").strip()
    signatures = headers.get("webhook-signature", "").split()
    if not message_id or not timestamp or not signatures:
        raise ProviderWebhookAuthenticationError("GitLab webhook signature is missing")
    try:
        sent_at = datetime.fromtimestamp(int(timestamp), UTC)
    except (ValueError, OverflowError) as error:
        raise ProviderWebhookAuthenticationError(
            "GitLab webhook timestamp is invalid"
        ) from error
    if abs((clock().astimezone(UTC) - sent_at).total_seconds()) > tolerance_seconds:
        raise ProviderWebhookAuthenticationError("GitLab webhook timestamp is stale")
    key = _signing_key(signing_token)
    message = f"{message_id}.{timestamp}.".encode() + body
    expected = "v1," + base64.b64encode(
        hmac.new(key, message, hashlib.sha256).digest()
    ).decode("ascii")
    if not any(hmac.compare_digest(expected, signature) for signature in signatures):
        raise ProviderWebhookAuthenticationError("invalid GitLab webhook signature")
    event = headers.get("x-gitlab-event", "").strip()
    if event not in _SUPPORTED_EVENTS:
        raise ProviderWebhookPayloadError("unsupported GitLab webhook event")
    payload = _json_object(body)
    if event == "Pipeline Hook":
        notification = _pipeline(payload, message_id, route)
    elif event == "Deployment Hook":
        notification = _deployment(payload, message_id, route)
    else:
        notification = _merge_request(payload, message_id, route)
    return ParsedProviderWebhook(notification, message_id)


def _pipeline(
    payload: dict[str, object], message_id: str, route: str
) -> CanonicalNotification:
    attributes = _object(payload, "object_attributes")
    project = _object(payload, "project")
    status = _text(attributes, "status")
    project_name = _text(project, "path_with_namespace")
    url = _https_url(attributes.get("url"))
    return _notification(
        message_id,
        route,
        title=f"GitLab pipeline {status}",
        body=f"GitLab pipeline for {project_name} completed with {status}.",
        severity=_result_severity(status),
        facts=(Fact("Project", project_name), Fact("Status", status)),
        url=url,
    )


def _deployment(
    payload: dict[str, object], message_id: str, route: str
) -> CanonicalNotification:
    status = _text(payload, "status")
    environment = _text(payload, "environment")
    project = _object(payload, "project")
    project_name = _text(project, "path_with_namespace")
    url = _https_url(payload.get("deployable_url"))
    return _notification(
        message_id,
        route,
        title=f"GitLab deployment {status}",
        body=(
            f"GitLab deployment for {project_name} in {environment} "
            f"changed to {status}."
        ),
        severity=_result_severity(status),
        facts=(
            Fact("Project", project_name),
            Fact("Environment", environment),
            Fact("Status", status),
        ),
        url=url,
    )


def _merge_request(
    payload: dict[str, object], message_id: str, route: str
) -> CanonicalNotification:
    attributes = _object(payload, "object_attributes")
    action = _text(attributes, "action")
    if action not in {"open", "reopen", "approval", "approved"}:
        raise ProviderWebhookPayloadError("unsupported GitLab merge request action")
    title = _text(attributes, "title")
    project = _object(payload, "project")
    project_name = _text(project, "path_with_namespace")
    url = _https_url(attributes.get("url"))
    return _notification(
        message_id,
        route,
        title="GitLab merge request review",
        body=f"Merge request {title} in {project_name} reported action {action}.",
        severity=Severity.SUCCESS if action == "approved" else Severity.WARNING,
        facts=(Fact("Project", project_name), Fact("Action", action)),
        url=url,
    )


def _notification(
    message_id: str,
    route: str,
    *,
    title: str,
    body: str,
    severity: Severity,
    facts: tuple[Fact, ...],
    url: str | None,
) -> CanonicalNotification:
    links = (Link("Open in GitLab", url),) if url is not None else ()
    return CanonicalNotification(
        schema_version="1.0",
        event_id=_safe_event_id(f"gitlab-{message_id}"),
        route=route,
        title=title[:150],
        body=body[:8000],
        severity=severity,
        facts=facts,
        links=links,
        metadata={"source": "gitlab-webhook", "correlationId": message_id[:128]},
    )


def _signing_key(token: str) -> bytes:
    if not token.startswith("whsec_"):
        raise ProviderWebhookAuthenticationError("GitLab signing token is invalid")
    encoded = token.removeprefix("whsec_")
    try:
        key = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ProviderWebhookAuthenticationError(
            "GitLab signing token is invalid"
        ) from error
    if len(key) < 16:
        raise ProviderWebhookAuthenticationError("GitLab signing token is invalid")
    return key


def _result_severity(status: str) -> Severity:
    if status in {"success", "successful", "succeeded"}:
        return Severity.SUCCESS
    if status in {"failed", "failure", "canceled", "cancelled"}:
        return Severity.ERROR
    return Severity.INFO


def _json_object(body: bytes) -> dict[str, object]:
    try:
        value: object = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProviderWebhookPayloadError("GitLab webhook body must be JSON") from error
    if not isinstance(value, dict):
        raise ProviderWebhookPayloadError("GitLab webhook body must be an object")
    return cast(dict[str, object], value)


def _object(value: dict[str, object], key: str) -> dict[str, object]:
    nested = value.get(key)
    if not isinstance(nested, dict):
        raise ProviderWebhookPayloadError(f"GitLab webhook field is invalid: {key}")
    return cast(dict[str, object], nested)


def _text(value: dict[str, object], key: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise ProviderWebhookPayloadError(f"GitLab webhook field is invalid: {key}")
    return raw.strip()


def _https_url(value: object) -> str | None:
    return (
        value.strip()
        if isinstance(value, str) and value.startswith("https://")
        else None
    )


def _safe_event_id(value: str) -> str:
    normalized = _EVENT_ID.sub("-", value).strip("-")[:128]
    if not normalized:
        raise ProviderWebhookPayloadError("GitLab webhook ID is invalid")
    return normalized
