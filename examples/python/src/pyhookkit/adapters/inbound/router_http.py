"""Authenticated HTTP boundary for the central notification router."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hmac import compare_digest
from http.server import BaseHTTPRequestHandler
from typing import ClassVar
from urllib.parse import urlsplit

from pyhookkit.adapters.inbound.canonical_notification_json import (
    CanonicalNotificationJsonError,
    canonical_notification_from_json,
)
from pyhookkit.adapters.outbound.routing_status_json import (
    routed_notification_status_to_json,
    submission_receipt_to_json,
)
from pyhookkit.application.notification_router import (
    NotificationConflictError,
    NotificationRouter,
    RouteNotConfiguredError,
)
from pyhookkit.json_types import JsonObject

_PRODUCER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_STATUS_PATH = re.compile(
    r"^/v1/notifications/"
    r"(?P<notification_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12})$"
)


class RouterAuthenticationError(ValueError):
    """Router producer credentials are missing or invalid."""


@dataclass(frozen=True, slots=True)
class RouterHttpResponse:
    """An HTTP response with a JSON-compatible body."""

    status_code: int
    body: JsonObject


class ProducerAuthenticator:
    """Authenticate isolated producer bearer credentials."""

    def __init__(self, secrets: Mapping[str, str]) -> None:
        if not secrets:
            raise ValueError("at least one producer credential is required")
        normalized: dict[str, str] = {}
        for producer, secret in secrets.items():
            if _PRODUCER.fullmatch(producer) is None:
                raise ValueError("producer must use lower-case kebab-case")
            if len(secret) < 16:
                raise ValueError(
                    f"producer credential must contain at least 16 characters: "
                    f"{producer}"
                )
            normalized[producer] = secret
        self._secrets = normalized

    def authenticate(self, headers: Mapping[str, str]) -> str:
        """Return the producer identity or raise one generic auth error."""
        producer = headers.get("x-pyhookkit-producer", "")
        authorization = headers.get("authorization", "")
        prefix = "Bearer "
        expected = self._secrets.get(producer)
        supplied = (
            authorization[len(prefix) :] if authorization.startswith(prefix) else ""
        )
        if expected is None or not supplied or not compare_digest(expected, supplied):
            raise RouterAuthenticationError("invalid router credentials")
        return producer


class RouterHttpApplication:
    """Map authenticated HTTP requests to the notification router."""

    def __init__(
        self,
        router: NotificationRouter,
        authenticator: ProducerAuthenticator,
        *,
        max_body_bytes: int = 64 * 1024,
    ) -> None:
        if max_body_bytes < 1:
            raise ValueError("maximum request body size must be positive")
        self._router = router
        self._authenticator = authenticator
        self.max_body_bytes = max_body_bytes

    def handle(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str],
        body: bytes = b"",
    ) -> RouterHttpResponse:
        """Handle one request without exposing credentials or payloads."""
        route_path = urlsplit(path).path
        if method == "GET" and route_path == "/healthz":
            return RouterHttpResponse(200, {"status": "ok"})

        try:
            producer = self._authenticator.authenticate(headers)
        except RouterAuthenticationError:
            return _error(401, "unauthorized", "invalid router credentials")

        if method == "POST" and route_path == "/v1/notifications":
            return self._submit(producer, headers, body)
        if method == "GET":
            match = _STATUS_PATH.fullmatch(route_path)
            if match is not None:
                status = self._router.status(
                    producer,
                    match.group("notification_id"),
                )
                if status is None:
                    return _error(
                        404,
                        "not_found",
                        "notification was not found",
                    )
                return RouterHttpResponse(
                    200,
                    routed_notification_status_to_json(status),
                )
        return _error(404, "not_found", "route was not found")

    def _submit(
        self,
        producer: str,
        headers: Mapping[str, str],
        body: bytes,
    ) -> RouterHttpResponse:
        content_type = headers.get("content-type", "").split(";", maxsplit=1)[0]
        if content_type.strip().lower() != "application/json":
            return _error(
                415,
                "unsupported_media_type",
                "content type must be application/json",
            )
        if len(body) > self.max_body_bytes:
            return _error(413, "payload_too_large", "request body is too large")
        try:
            value: object = json.loads(body.decode("utf-8"))
            notification = canonical_notification_from_json(value)
            receipt = self._router.submit(producer, notification)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error(400, "invalid_json", "request body must be valid JSON")
        except CanonicalNotificationJsonError as error:
            return _error(422, "invalid_notification", str(error))
        except RouteNotConfiguredError as error:
            return _error(422, "route_not_configured", str(error))
        except NotificationConflictError as error:
            return _error(409, "event_conflict", str(error))
        return RouterHttpResponse(202, submission_receipt_to_json(receipt))


class RouterRequestHandler(BaseHTTPRequestHandler):
    """Thin standard-library HTTP transport for RouterHttpApplication."""

    application: ClassVar[RouterHttpApplication]
    server_version = "PyHookKitRouter/0.1"

    def do_GET(self) -> None:
        """Serve health and notification status."""
        self._dispatch("GET")

    def do_POST(self) -> None:
        """Accept one canonical notification."""
        self._dispatch("POST")

    def log_message(self, format: str, *args: object) -> None:
        """Suppress request logging because paths may become sensitive."""
        del format, args

    def _dispatch(self, method: str) -> None:
        body = b""
        if method == "POST":
            raw_content_length = self.headers.get("Content-Length")
            if raw_content_length is None:
                self._write(
                    _error(411, "length_required", "Content-Length is required")
                )
                return
            try:
                content_length = int(raw_content_length)
            except ValueError:
                self._write(_error(400, "invalid_length", "Content-Length is invalid"))
                return
            if content_length < 0:
                self._write(_error(400, "invalid_length", "Content-Length is invalid"))
                return
            if content_length > self.application.max_body_bytes:
                self._write(
                    _error(
                        413,
                        "payload_too_large",
                        "request body is too large",
                    )
                )
                return
            body = self.rfile.read(content_length)

        headers = {key.lower(): value for key, value in self.headers.items()}
        self._write(
            self.application.handle(
                method,
                self.path,
                headers,
                body,
            )
        )

    def _write(self, response: RouterHttpResponse) -> None:
        encoded = json.dumps(response.body, separators=(",", ":")).encode("utf-8")
        self.send_response(response.status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


def _error(status_code: int, code: str, message: str) -> RouterHttpResponse:
    return RouterHttpResponse(
        status_code,
        {
            "error": {
                "code": code,
                "message": message,
            }
        },
    )
