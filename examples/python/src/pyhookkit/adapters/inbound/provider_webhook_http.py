"""HTTP application for provider-native webhook authentication and ingestion."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from pyhookkit.adapters.inbound.azure_devops_webhook import (
    parse_azure_devops_webhook,
)
from pyhookkit.adapters.inbound.github_webhook import parse_github_webhook
from pyhookkit.adapters.inbound.gitlab_webhook import parse_gitlab_webhook
from pyhookkit.adapters.inbound.provider_webhook import (
    ParsedProviderWebhook,
    ProviderWebhookAuthenticationError,
    ProviderWebhookPayloadError,
)
from pyhookkit.adapters.outbound.routing_status_json import submission_receipt_to_json
from pyhookkit.application.notification_router import (
    NotificationConflictError,
    NotificationRouter,
    RouteNotConfiguredError,
)
from pyhookkit.json_types import JsonObject
from pyhookkit.ports.inbound_integrations import (
    InboundIntegration,
    InboundIntegrationStore,
)

_PATH = re.compile(
    r"^/v1/inbound/(?P<provider>github|gitlab|azure-devops)/"
    r"(?P<integration_id>[a-z0-9]+(?:-[a-z0-9]+)*)$"
)


@dataclass(frozen=True, slots=True)
class ProviderWebhookHttpResponse:
    """A provider webhook response with no provider payload content."""

    status_code: int
    body: JsonObject


class ProviderWebhookHttpApplication:
    """Authenticate provider requests and submit transformed notifications."""

    def __init__(
        self,
        router: NotificationRouter,
        integrations: InboundIntegrationStore,
        environment: Mapping[str, str],
        *,
        max_body_bytes: int = 64 * 1024,
    ) -> None:
        if max_body_bytes < 1:
            raise ValueError("maximum webhook body size must be positive")
        self._router = router
        self._integrations = integrations
        self._environment = environment
        self.max_body_bytes = max_body_bytes

    def handles(self, method: str, path: str) -> bool:
        """Return whether this application owns the request path."""
        return method == "POST" and _PATH.fullmatch(path) is not None

    def handle(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str],
        body: bytes,
    ) -> ProviderWebhookHttpResponse:
        """Handle one provider-native webhook without logging its body."""
        match = _PATH.fullmatch(path) if method == "POST" else None
        if match is None:
            return _error(404, "not_found", "route was not found")
        if len(body) > self.max_body_bytes:
            return _error(413, "payload_too_large", "request body is too large")
        content_type = headers.get("content-type", "").split(";", maxsplit=1)[0]
        if content_type.strip().lower() != "application/json":
            return _error(
                415,
                "unsupported_media_type",
                "content type must be application/json",
            )
        integration = self._integrations.integration(match.group("integration_id"))
        if (
            integration is None
            or not integration.enabled
            or integration.provider != match.group("provider")
        ):
            return _error(404, "not_found", "integration was not found")
        secret = self._environment.get(
            integration.secret_environment_variable, ""
        ).strip()
        if not secret:
            return _error(503, "integration_unavailable", "integration is unavailable")
        try:
            parsed = self._parse(integration, body, headers, secret)
            receipt = (
                self._router.submit(integration.producer, parsed.notification)
                if integration.target_id is None
                else self._router.submit_to_target(
                    integration.producer,
                    integration.target_id,
                    parsed.notification,
                )
            )
        except ProviderWebhookAuthenticationError:
            return _error(401, "unauthorized", "invalid webhook credentials")
        except ProviderWebhookPayloadError as error:
            return _error(422, "unsupported_event", str(error))
        except RouteNotConfiguredError as error:
            return _error(422, "route_not_configured", str(error))
        except NotificationConflictError as error:
            return _error(409, "event_conflict", str(error))
        self._integrations.mark_received(integration.integration_id, datetime.now(UTC))
        response = submission_receipt_to_json(receipt)
        response["integrationId"] = integration.integration_id
        if integration.target_id is not None:
            response["targetId"] = integration.target_id
        return ProviderWebhookHttpResponse(202, response)

    @staticmethod
    def _parse(
        integration: InboundIntegration,
        body: bytes,
        headers: Mapping[str, str],
        secret: str,
    ) -> ParsedProviderWebhook:
        if integration.provider == "github":
            return parse_github_webhook(
                body,
                headers,
                secret=secret,
                route=integration.route,
            )
        if integration.provider == "gitlab":
            return parse_gitlab_webhook(
                body,
                headers,
                signing_token=secret,
                route=integration.route,
            )
        if integration.username is None:
            raise ProviderWebhookPayloadError(
                "Azure DevOps webhook username is not configured"
            )
        return parse_azure_devops_webhook(
            body,
            headers,
            username=integration.username,
            password=secret,
            route=integration.route,
        )


def _error(status_code: int, code: str, message: str) -> ProviderWebhookHttpResponse:
    return ProviderWebhookHttpResponse(
        status_code,
        {"error": {"code": code, "message": message}},
    )
