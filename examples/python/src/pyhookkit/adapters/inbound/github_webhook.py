"""GitHub webhook authentication and canonical event transformation."""

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from typing import cast

from pyhookkit.adapters.inbound.provider_webhook import (
    ParsedProviderWebhook,
    ProviderWebhookAuthenticationError,
    ProviderWebhookPayloadError,
)
from pyhookkit.domain.notification import CanonicalNotification, Fact, Link, Severity

_EVENT_ID = re.compile(r"[^A-Za-z0-9._:-]+")
_SUPPORTED_EVENTS = frozenset(
    {"ping", "workflow_run", "deployment_status", "pull_request"}
)


def parse_github_webhook(
    body: bytes,
    headers: Mapping[str, str],
    *,
    secret: str,
    route: str,
) -> ParsedProviderWebhook:
    """Authenticate and transform one supported GitHub webhook delivery."""
    signature = headers.get("x-hub-signature-256", "")
    expected = (
        "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    )
    if not signature or not hmac.compare_digest(expected, signature):
        raise ProviderWebhookAuthenticationError("invalid GitHub webhook signature")
    delivery_id = headers.get("x-github-delivery", "").strip()
    event = headers.get("x-github-event", "").strip()
    if not delivery_id or event not in _SUPPORTED_EVENTS:
        raise ProviderWebhookPayloadError("unsupported GitHub webhook event")
    value = _json_object(body)
    if event == "ping":
        notification = _ping(value, delivery_id, route)
    elif event == "workflow_run":
        notification = _workflow_run(value, delivery_id, route)
    elif event == "deployment_status":
        notification = _deployment_status(value, delivery_id, route)
    else:
        notification = _pull_request(value, delivery_id, route)
    return ParsedProviderWebhook(notification, delivery_id)


def _ping(
    payload: dict[str, object], delivery_id: str, route: str
) -> CanonicalNotification:
    repository = _repository_name(payload)
    repository_object = _object(payload, "repository")
    url = _https_url(repository_object.get("html_url"))
    return _notification(
        delivery_id,
        route,
        title="GitHub Webhook connection verified",
        body=f"GitHub successfully connected the Webhook for {repository}.",
        severity=Severity.INFO,
        facts=(Fact("Repository", repository), Fact("Event", "ping")),
        url=url,
        source="github-webhook",
    )


def _workflow_run(
    payload: dict[str, object], delivery_id: str, route: str
) -> CanonicalNotification:
    run = _object(payload, "workflow_run")
    name = _text(run, "name")
    conclusion = _text(run, "conclusion")
    repository = _repository_name(payload)
    url = _https_url(run.get("html_url"))
    severity = Severity.SUCCESS if conclusion == "success" else Severity.ERROR
    facts = (
        Fact("Repository", repository),
        Fact("Workflow", name),
        Fact("Conclusion", conclusion),
    )
    return _notification(
        delivery_id,
        route,
        title=f"GitHub workflow {conclusion}",
        body=f"GitHub workflow {name} for {repository} completed with {conclusion}.",
        severity=severity,
        facts=facts,
        url=url,
        source="github-webhook",
    )


def _deployment_status(
    payload: dict[str, object], delivery_id: str, route: str
) -> CanonicalNotification:
    status = _object(payload, "deployment_status")
    deployment = _object(payload, "deployment")
    state = _text(status, "state")
    environment = _optional_text(deployment.get("environment")) or "unspecified"
    repository = _repository_name(payload)
    url = _https_url(status.get("target_url")) or _https_url(
        status.get("environment_url")
    )
    severity = Severity.SUCCESS if state == "success" else Severity.ERROR
    return _notification(
        delivery_id,
        route,
        title=f"GitHub deployment {state}",
        body=(
            f"GitHub deployment for {repository} in {environment} changed to {state}."
        ),
        severity=severity,
        facts=(
            Fact("Repository", repository),
            Fact("Environment", environment),
            Fact("State", state),
        ),
        url=url,
        source="github-webhook",
    )


def _pull_request(
    payload: dict[str, object], delivery_id: str, route: str
) -> CanonicalNotification:
    action = _text(payload, "action")
    if action not in {"review_requested", "opened", "reopened"}:
        raise ProviderWebhookPayloadError("unsupported GitHub pull request action")
    pull_request = _object(payload, "pull_request")
    title = _text(pull_request, "title")
    repository = _repository_name(payload)
    url = _https_url(pull_request.get("html_url"))
    return _notification(
        delivery_id,
        route,
        title="GitHub pull request review requested",
        body=f"Review requested for {title} in {repository}.",
        severity=Severity.WARNING,
        facts=(Fact("Repository", repository), Fact("Action", action)),
        url=url,
        source="github-webhook",
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
    source: str,
) -> CanonicalNotification:
    links = (Link("Open in GitHub", url),) if url is not None else ()
    return CanonicalNotification(
        schema_version="1.0",
        event_id=_safe_event_id(f"github-{delivery_id}"),
        route=route,
        title=title[:150],
        body=body[:8000],
        severity=severity,
        facts=facts,
        links=links,
        metadata={"source": source, "correlationId": delivery_id[:128]},
    )


def _json_object(body: bytes) -> dict[str, object]:
    try:
        value: object = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProviderWebhookPayloadError("GitHub webhook body must be JSON") from error
    if not isinstance(value, dict):
        raise ProviderWebhookPayloadError("GitHub webhook body must be an object")
    return cast(dict[str, object], value)


def _object(value: dict[str, object], key: str) -> dict[str, object]:
    nested = value.get(key)
    if not isinstance(nested, dict):
        raise ProviderWebhookPayloadError(f"GitHub webhook field is invalid: {key}")
    return cast(dict[str, object], nested)


def _text(value: dict[str, object], key: str) -> str:
    text = _optional_text(value.get(key))
    if text is None:
        raise ProviderWebhookPayloadError(f"GitHub webhook field is invalid: {key}")
    return text


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _repository_name(payload: dict[str, object]) -> str:
    repository = _object(payload, "repository")
    return _text(repository, "full_name")


def _https_url(value: object) -> str | None:
    text = _optional_text(value)
    return text if text is not None and text.startswith("https://") else None


def _safe_event_id(value: str) -> str:
    normalized = _EVENT_ID.sub("-", value).strip("-")[:128]
    if not normalized:
        raise ProviderWebhookPayloadError("GitHub delivery ID is invalid")
    return normalized
