"""Authenticated HTTP boundary for the local router administration UI."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hmac import compare_digest
from http.server import BaseHTTPRequestHandler
from importlib.resources import files
from typing import ClassVar, Protocol, cast
from urllib.parse import urlsplit

from pyhookkit.json_types import JsonObject

_DASHBOARD_HTML = (
    files("pyhookkit.adapters.inbound").joinpath("admin_dashboard.html").read_bytes()
)
_TEST_DESTINATION_PATH = re.compile(
    r"^/admin/api/destinations/"
    r"(?P<target_id>[a-z0-9]+(?:-[a-z0-9]+)*)/test$"
)
_API_KEY_PATH = re.compile(r"^/admin/api/api-keys/(?P<key_id>[0-9a-f]{12})$")


class RouterAdminController(Protocol):
    """Redacted administration operations exposed to the HTTP adapter."""

    def destinations(self) -> tuple[JsonObject, ...]: ...

    def notifications(self) -> tuple[JsonObject, ...]: ...

    def add_teams_channel(self, *, route: str, channel_link: str) -> JsonObject: ...

    def test_destination(self, target_id: str) -> JsonObject: ...

    def api_keys(self) -> tuple[JsonObject, ...]: ...

    def issue_api_key(
        self,
        *,
        producer: str,
        route: str | None,
        target_id: str | None,
    ) -> JsonObject: ...

    def revoke_api_key(self, key_id: str) -> bool: ...

    def integrations(self) -> tuple[JsonObject, ...]: ...

    def add_integration(self, value: JsonObject) -> JsonObject: ...


@dataclass(frozen=True, slots=True)
class AdminHttpResponse:
    """One encoded administration response."""

    status_code: int
    body: bytes
    content_type: str


class AdminAuthenticator:
    """Verify one dedicated administration bearer token."""

    def __init__(self, token: str) -> None:
        if len(token) < 24:
            raise ValueError("administrator token must contain at least 24 characters")
        self._token = token

    def authenticate(self, headers: Mapping[str, str]) -> bool:
        """Return whether the request contains the administrator bearer token."""
        authorization = headers.get("authorization", "")
        prefix = "Bearer "
        supplied = (
            authorization[len(prefix) :] if authorization.startswith(prefix) else ""
        )
        return bool(supplied) and compare_digest(self._token, supplied)


class RouterAdminHttpApplication:
    """Serve the dashboard and map authenticated API requests to administration."""

    max_body_bytes = 16 * 1024

    def __init__(
        self,
        controller: RouterAdminController,
        authenticator: AdminAuthenticator,
    ) -> None:
        self._controller = controller
        self._authenticator = authenticator

    def handle(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str],
        body: bytes = b"",
    ) -> AdminHttpResponse:
        """Handle one dashboard or administration API request."""
        route_path = urlsplit(path).path
        if method == "GET" and route_path in {"/admin", "/admin/"}:
            return AdminHttpResponse(200, _DASHBOARD_HTML, "text/html; charset=utf-8")
        if not route_path.startswith("/admin/api/"):
            return _json_response(404, _error("not_found", "route was not found"))
        if not self._authenticator.authenticate(headers):
            return _json_response(
                401,
                _error("unauthorized", "invalid administrator credentials"),
            )
        if method == "GET" and route_path == "/admin/api/destinations":
            return _json_response(200, {"items": list(self._controller.destinations())})
        if method == "GET" and route_path == "/admin/api/notifications":
            return _json_response(
                200, {"items": list(self._controller.notifications())}
            )
        if method == "GET" and route_path == "/admin/api/api-keys":
            return _json_response(200, {"items": list(self._controller.api_keys())})
        if method == "GET" and route_path == "/admin/api/integrations":
            return _json_response(
                200,
                {"items": list(self._controller.integrations())},
            )
        if method == "DELETE":
            key_match = _API_KEY_PATH.fullmatch(route_path)
            if key_match is not None:
                revoked = self._controller.revoke_api_key(key_match.group("key_id"))
                if not revoked:
                    return _json_response(
                        404,
                        _error("not_found", "API key was not found"),
                    )
                return _json_response(200, {"state": "revoked"})
        if method == "POST":
            test_match = _TEST_DESTINATION_PATH.fullmatch(route_path)
            if test_match is not None:
                result = self._controller.test_destination(
                    test_match.group("target_id")
                )
                status_code = 200 if result.get("state") == "succeeded" else 502
                return _json_response(status_code, result)
        if method == "POST" and route_path == "/admin/api/destinations":
            return self._add_destination(headers, body)
        if method == "POST" and route_path == "/admin/api/api-keys":
            return self._issue_api_key(headers, body)
        if method == "POST" and route_path == "/admin/api/integrations":
            return self._add_integration(headers, body)
        return _json_response(404, _error("not_found", "route was not found"))

    def _issue_api_key(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> AdminHttpResponse:
        value = self._json_object(headers, body)
        if isinstance(value, AdminHttpResponse):
            return value
        allowed = {"producer", "route", "targetId"}
        if not set(value) <= allowed or "producer" not in value:
            return _json_response(
                422,
                _error("invalid_api_key", "API key request fields are invalid"),
            )
        producer = value.get("producer")
        route = value.get("route")
        target_id = value.get("targetId")
        if (
            not isinstance(producer, str)
            or (route is not None and not isinstance(route, str))
            or (target_id is not None and not isinstance(target_id, str))
        ):
            return _json_response(
                422,
                _error("invalid_api_key", "API key request values are invalid"),
            )
        try:
            result = self._controller.issue_api_key(
                producer=producer.strip(),
                route=route.strip() if isinstance(route, str) else None,
                target_id=(target_id.strip() if isinstance(target_id, str) else None),
            )
        except ValueError as error:
            return _json_response(422, _error("invalid_api_key", str(error)))
        return _json_response(201, result)

    def _add_integration(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> AdminHttpResponse:
        value = self._json_object(headers, body)
        if isinstance(value, AdminHttpResponse):
            return value
        try:
            result = self._controller.add_integration(value)
        except ValueError as error:
            return _json_response(422, _error("invalid_integration", str(error)))
        return _json_response(201, result)

    def _json_object(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> JsonObject | AdminHttpResponse:
        content_type = headers.get("content-type", "").split(";", maxsplit=1)[0]
        if content_type.strip().lower() != "application/json":
            return _json_response(
                415,
                _error(
                    "unsupported_media_type",
                    "content type must be application/json",
                ),
            )
        if len(body) > self.max_body_bytes:
            return _json_response(
                413,
                _error("payload_too_large", "request body is too large"),
            )
        try:
            value: object = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _json_response(
                400,
                _error("invalid_json", "request body must be valid JSON"),
            )
        if not isinstance(value, dict):
            return _json_response(
                422,
                _error("invalid_request", "request body must be an object"),
            )
        return cast(JsonObject, value)

    def _add_destination(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> AdminHttpResponse:
        content_type = headers.get("content-type", "").split(";", maxsplit=1)[0]
        if content_type.strip().lower() != "application/json":
            return _json_response(
                415,
                _error(
                    "unsupported_media_type", "content type must be application/json"
                ),
            )
        if len(body) > self.max_body_bytes:
            return _json_response(
                413,
                _error("payload_too_large", "request body is too large"),
            )
        try:
            value: object = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _json_response(
                400,
                _error("invalid_json", "request body must be valid JSON"),
            )
        if not isinstance(value, dict):
            return _json_response(
                422,
                _error("invalid_destination", "request body must be an object"),
            )
        value_object = cast(dict[str, object], value)
        if set(value_object) != {"route", "channelLink"}:
            return _json_response(
                422,
                _error(
                    "invalid_destination",
                    "request must contain only route and channelLink",
                ),
            )
        route = value_object.get("route")
        channel_link = value_object.get("channelLink")
        if not isinstance(route, str) or not isinstance(channel_link, str):
            return _json_response(
                422,
                _error("invalid_destination", "route and channelLink must be strings"),
            )
        try:
            result = self._controller.add_teams_channel(
                route=route.strip(),
                channel_link=channel_link.strip(),
            )
        except ValueError as error:
            return _json_response(422, _error("invalid_destination", str(error)))
        return _json_response(201, result)


class RouterAdminRequestHandler(BaseHTTPRequestHandler):
    """Standard-library transport for the router administration application."""

    application: ClassVar[RouterAdminHttpApplication]
    server_version = "PyHookKitAdmin/0.1"

    def do_GET(self) -> None:
        """Serve the dashboard and read-only administration data."""
        self._dispatch("GET")

    def do_POST(self) -> None:
        """Apply one authenticated administration operation."""
        self._dispatch("POST")

    def do_DELETE(self) -> None:
        """Revoke one authenticated administration resource."""
        self._dispatch("DELETE")

    def log_message(self, format: str, *args: object) -> None:
        """Suppress paths and authorization-related request metadata."""
        del format, args

    def _dispatch(self, method: str) -> None:
        body = b""
        if method == "POST":
            raw_content_length = self.headers.get("Content-Length")
            try:
                content_length = int(raw_content_length or "")
            except ValueError:
                self._write(
                    _json_response(
                        400, _error("invalid_length", "Content-Length is invalid")
                    )
                )
                return
            if content_length < 0:
                self._write(
                    _json_response(
                        400, _error("invalid_length", "Content-Length is invalid")
                    )
                )
                return
            if content_length > self.application.max_body_bytes:
                self._write(
                    _json_response(
                        413,
                        _error("payload_too_large", "request body is too large"),
                    )
                )
                return
            body = self.rfile.read(content_length)
        headers = {key.lower(): value for key, value in self.headers.items()}
        self._write(self.application.handle(method, self.path, headers, body))

    def _write(self, response: AdminHttpResponse) -> None:
        self.send_response(response.status_code)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'unsafe-inline'; "
            "style-src 'unsafe-inline'; "
            "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(response.body)


def _json_response(status_code: int, body: JsonObject) -> AdminHttpResponse:
    encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
    return AdminHttpResponse(status_code, encoded, "application/json")


def _error(code: str, message: str) -> JsonObject:
    return {"error": {"code": code, "message": message}}
