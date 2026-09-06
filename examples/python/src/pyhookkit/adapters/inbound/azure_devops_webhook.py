"""Azure DevOps Service Hooks basic authentication and event transformation."""

import base64
import binascii
import json
import re
from collections.abc import Mapping
from hmac import compare_digest
from typing import cast

from pyhookkit.adapters.inbound.provider_webhook import (
    ParsedProviderWebhook,
    ProviderWebhookAuthenticationError,
    ProviderWebhookPayloadError,
)
from pyhookkit.domain.notification import CanonicalNotification, Fact, Link, Severity

_EVENT_ID = re.compile(r"[^A-Za-z0-9._:-]+")
_SUPPORTED_EVENTS = frozenset(
    {"build.complete", "ms.vss-release.deployment-completed-event"}
)


def parse_azure_devops_webhook(
    body: bytes,
    headers: Mapping[str, str],
    *,
    username: str,
    password: str,
    route: str,
) -> ParsedProviderWebhook:
    """Authenticate and transform one Azure DevOps Service Hook request."""
    _verify_basic_auth(headers.get("authorization", ""), username, password)
    payload = _json_object(body)
    event = _text(payload, "eventType")
    delivery_id = _text(payload, "id")
    if event not in _SUPPORTED_EVENTS:
        raise ProviderWebhookPayloadError("unsupported Azure DevOps service hook event")
    notification = (
        _build(payload, delivery_id, route)
        if event == "build.complete"
        else _release_deployment(payload, delivery_id, route)
    )
    return ParsedProviderWebhook(notification, delivery_id)


def _verify_basic_auth(authorization: str, username: str, password: str) -> None:
    prefix = "Basic "
    if not authorization.startswith(prefix):
        raise ProviderWebhookAuthenticationError(
            "invalid Azure DevOps webhook credentials"
        )
    try:
        decoded = base64.b64decode(authorization[len(prefix) :], validate=True).decode(
            "utf-8"
        )
    except (binascii.Error, UnicodeDecodeError) as error:
        raise ProviderWebhookAuthenticationError(
            "invalid Azure DevOps webhook credentials"
        ) from error
    expected = f"{username}:{password}"
    if not compare_digest(decoded, expected):
        raise ProviderWebhookAuthenticationError(
            "invalid Azure DevOps webhook credentials"
        )


def _build(
    payload: dict[str, object], delivery_id: str, route: str
) -> CanonicalNotification:
    resource = _object(payload, "resource")
    build_number = _text(resource, "buildNumber")
    result = _text(resource, "result")
    status = _text(resource, "status")
    url = _web_url(resource)
    return _notification(
        delivery_id,
        route,
        title=f"Azure Pipelines build {result}",
        body=(
            f"Azure Pipelines build {build_number} completed with {result} "
            f"and status {status}."
        ),
        severity=_result_severity(result),
        facts=(
            Fact("Build", build_number),
            Fact("Result", result),
            Fact("Status", status),
        ),
        url=url,
    )


def _release_deployment(
    payload: dict[str, object], delivery_id: str, route: str
) -> CanonicalNotification:
    resource = _object(payload, "resource")
    deployment = _object(resource, "deployment")
    environment = _object(resource, "environment")
    release = _object(resource, "release")
    status = _text(deployment, "deploymentStatus")
    environment_name = _text(environment, "name")
    release_name = _text(release, "name")
    url = _web_url(release)
    return _notification(
        delivery_id,
        route,
        title=f"Azure DevOps deployment {status}",
        body=(
            f"Azure DevOps release {release_name} deployment to "
            f"{environment_name} completed with {status}."
        ),
        severity=_result_severity(status),
        facts=(
            Fact("Release", release_name),
            Fact("Environment", environment_name),
            Fact("Status", status),
        ),
        url=url,
    )


def _notification(
    delivery_id: str,
    route: str,
    *,
    title: str,
    body: str,
    severity: Severity,
    facts: tuple[Fact, ...],
    url: str | None,
) -> CanonicalNotification:
    links = (Link("Open in Azure DevOps", url),) if url is not None else ()
    return CanonicalNotification(
        schema_version="1.0",
        event_id=_safe_event_id(f"azure-devops-{delivery_id}"),
        route=route,
        title=title[:150],
        body=body[:8000],
        severity=severity,
        facts=facts,
        links=links,
        metadata={"source": "azure-devops", "correlationId": delivery_id[:128]},
    )


def _result_severity(result: str) -> Severity:
    if result.lower() in {"succeeded", "success", "partiallysucceeded"}:
        return Severity.SUCCESS
    if result.lower() in {"failed", "failure", "canceled", "cancelled"}:
        return Severity.ERROR
    return Severity.INFO


def _json_object(body: bytes) -> dict[str, object]:
    try:
        value: object = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProviderWebhookPayloadError(
            "Azure DevOps webhook body must be JSON"
        ) from error
    if not isinstance(value, dict):
        raise ProviderWebhookPayloadError("Azure DevOps webhook body must be an object")
    return cast(dict[str, object], value)


def _object(value: dict[str, object], key: str) -> dict[str, object]:
    nested = value.get(key)
    if not isinstance(nested, dict):
        raise ProviderWebhookPayloadError(
            f"Azure DevOps webhook field is invalid: {key}"
        )
    return cast(dict[str, object], nested)


def _text(value: dict[str, object], key: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise ProviderWebhookPayloadError(
            f"Azure DevOps webhook field is invalid: {key}"
        )
    return raw.strip()


def _web_url(value: dict[str, object]) -> str | None:
    links = value.get("_links")
    if not isinstance(links, dict):
        return None
    links_object = cast(dict[str, object], links)
    web = links_object.get("web")
    if not isinstance(web, dict):
        return None
    web_object = cast(dict[str, object], web)
    current = web_object.get("href")
    return (
        current.strip()
        if isinstance(current, str) and current.startswith("https://")
        else None
    )


def _safe_event_id(value: str) -> str:
    normalized = _EVENT_ID.sub("-", value).strip("-")[:128]
    if not normalized:
        raise ProviderWebhookPayloadError("Azure DevOps event ID is invalid")
    return normalized
