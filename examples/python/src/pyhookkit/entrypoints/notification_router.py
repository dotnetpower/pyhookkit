"""Composition root for the SQLite-backed central notification router."""

import argparse
import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from typing import cast
from uuid import UUID, uuid4

from pyhookkit.adapters.inbound.admin_http import (
    AdminAuthenticator,
    RouterAdminHttpApplication,
    RouterAdminRequestHandler,
)
from pyhookkit.adapters.inbound.provider_webhook_http import (
    ProviderWebhookHttpApplication,
)
from pyhookkit.adapters.inbound.router_http import (
    CompositeProducerAuthenticator,
    ProducerAuthenticator,
    RouterHttpApplication,
    RouterRequestHandler,
)
from pyhookkit.adapters.outbound.configured_notification_delivery import (
    ConfiguredNotificationDelivery,
)
from pyhookkit.adapters.outbound.router_client import NotificationRouterUrl
from pyhookkit.adapters.outbound.runtime_environment_file import (
    RuntimeEnvironmentFile,
    RuntimeEnvironmentFileError,
)
from pyhookkit.adapters.outbound.sqlite_inbound_integrations import (
    SqliteInboundIntegrationStore,
)
from pyhookkit.adapters.outbound.sqlite_producer_credentials import (
    SqliteProducerApiKeyStore,
)
from pyhookkit.adapters.outbound.sqlite_route_store import (
    SqliteRouteStore,
    StoredDestination,
)
from pyhookkit.adapters.outbound.teams.channel_link import TeamsChannelLink
from pyhookkit.adapters.outbound.teams.channel_membership import (
    TeamsGraphChannelMembershipProvisioner,
)
from pyhookkit.adapters.outbound.teams.channel_metadata import (
    TeamsChannelMembershipType,
    TeamsGraphChannelInspector,
)
from pyhookkit.adapters.outbound.teams.entra_app_bootstrap import (
    AzureCliTeamsNotifyAppBootstrapper,
    TeamsNotifyAppBootstrapError,
    TeamsNotifyAppSecret,
)
from pyhookkit.adapters.outbound.teams.graph_membership import (
    MicrosoftGraphAccessToken,
    TeamMembershipResult,
    TeamsGraphMembershipError,
    TeamsGraphMembershipProvisioner,
)
from pyhookkit.adapters.outbound.teams.graph_token import (
    MicrosoftGraphClientCredentialsTokenProvider,
    MicrosoftGraphTokenError,
    TeamsNotifyAppCredentials,
)
from pyhookkit.adapters.outbound.teams.workflow_url import TeamsWorkflowUrl
from pyhookkit.application.notification_router import NotificationRouter
from pyhookkit.application.notification_worker import NotificationWorker
from pyhookkit.domain.notification import CanonicalNotification, Severity
from pyhookkit.json_types import JsonObject, JsonValue
from pyhookkit.ports.inbound_integrations import InboundIntegration
from pyhookkit.ports.notification_routing import RoutedNotificationDelivery

_REPOSITORY_ENV_FILE = Path(__file__).resolve().parents[5] / ".env"
_TARGET_SLUG = re.compile(r"[^a-z0-9]+")


class SqliteRouterAdminController:
    """Compose redacted dashboard operations from concrete router adapters."""

    def __init__(
        self,
        store: SqliteRouteStore,
        environment: Mapping[str, str],
        delivery: RoutedNotificationDelivery | None = None,
        api_keys: SqliteProducerApiKeyStore | None = None,
        integrations: SqliteInboundIntegrationStore | None = None,
    ) -> None:
        self._store = store
        self._environment = environment
        self._delivery = delivery or ConfiguredNotificationDelivery(
            store,
            environment,
        )
        self._api_keys = api_keys
        self._integrations = integrations

    def destinations(self) -> tuple[JsonObject, ...]:
        """List Teams destinations without channel links or credentials."""
        base_url = NotificationRouterUrl(
            self._environment.get(
                "NOTIFICATION_ROUTER_URL",
                "http://127.0.0.1:8080",
            )
            or "http://127.0.0.1:8080"
        ).value.rstrip("/")
        return tuple(
            {
                "targetId": destination.target_id,
                "route": destination.route,
                "provider": destination.provider,
                "channelName": destination.channel_name,
                "teamId": destination.team_id,
                "channelId": destination.channel_id,
                "membershipType": destination.membership_type or "unknown",
                "enabled": destination.enabled,
                "webhookUrl": (
                    f"{base_url}/v1/destinations/{destination.target_id}/notifications"
                ),
            }
            for destination in self._store.destinations()
            if destination.provider == "teams-workflow"
        )

    def notifications(self) -> tuple[JsonObject, ...]:
        """List recent delivery state without canonical payload content."""
        output: list[JsonObject] = []
        for notification in self._store.recent_notifications():
            deliveries: list[JsonValue] = []
            for delivery in notification.deliveries:
                item: JsonObject = {
                    "targetId": delivery.target_id,
                    "state": delivery.state.value,
                    "attempts": delivery.attempts,
                }
                if delivery.error_kind is not None:
                    item["errorKind"] = delivery.error_kind.value
                if delivery.status_code is not None:
                    item["statusCode"] = delivery.status_code
                deliveries.append(item)
            output.append(
                {
                    "notificationId": notification.notification_id,
                    "producer": notification.producer,
                    "eventId": notification.event_id,
                    "createdAt": notification.created_at,
                    "state": notification.state.value,
                    "deliveries": deliveries,
                }
            )
        return tuple(output)

    def api_keys(self) -> tuple[JsonObject, ...]:
        """List redacted producer API-key metadata."""
        store = self._required_api_key_store()
        return tuple(
            {
                "keyId": key.key_id,
                "producer": key.producer,
                "route": key.route,
                "targetId": key.target_id,
                "createdAt": key.created_at,
                "revokedAt": key.revoked_at,
                "lastUsedAt": key.last_used_at,
                "state": "revoked" if key.revoked_at is not None else "active",
            }
            for key in store.list_keys()
        )

    def issue_api_key(
        self,
        *,
        producer: str,
        route: str | None,
        target_id: str | None,
    ) -> JsonObject:
        """Issue one producer API key and reveal its value exactly once."""
        if target_id is not None:
            destination = self._store.destination(target_id)
            if destination is None or not destination.enabled:
                raise ValueError("API key target is not configured")
            if route is not None and route != destination.route:
                raise ValueError("API key route does not match target")
            route = None
        elif route is not None and not any(
            destination.route == route and destination.enabled
            for destination in self._store.destinations()
        ):
            raise ValueError("API key route is not configured")
        issued = self._required_api_key_store().issue(
            producer,
            route=route,
            target_id=target_id,
        )
        return {
            "keyId": issued.key_id,
            "producer": issued.producer,
            "apiKey": issued.value,
            "route": issued.route,
            "targetId": issued.target_id,
            "createdAt": issued.created_at,
            "state": "active",
        }

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke one producer API key by its non-secret identifier."""
        return self._required_api_key_store().revoke(key_id)

    def integrations(self) -> tuple[JsonObject, ...]:
        """List provider-native integrations without secret values."""
        base_url = self._router_base_url()
        return tuple(
            {
                "integrationId": integration.integration_id,
                "provider": integration.provider,
                "producer": integration.producer,
                "route": integration.route,
                "targetId": integration.target_id,
                "username": integration.username,
                "enabled": integration.enabled,
                "createdAt": integration.created_at,
                "lastReceivedAt": integration.last_received_at,
                "webhookUrl": (
                    f"{base_url}/v1/inbound/{integration.provider}/"
                    f"{integration.integration_id}"
                ),
                "secretConfigured": bool(
                    self._environment.get(
                        integration.secret_environment_variable,
                        "",
                    ).strip()
                ),
            }
            for integration in self._required_integration_store().integrations()
        )

    def add_integration(self, value: JsonObject) -> JsonObject:
        """Register one non-secret provider-native inbound integration."""
        allowed = {
            "integrationId",
            "provider",
            "producer",
            "secretEnvironmentVariable",
            "route",
            "targetId",
            "username",
            "enabled",
        }
        if set(value) - allowed:
            raise ValueError("integration request contains unsupported fields")
        required = {
            "integrationId",
            "provider",
            "producer",
            "secretEnvironmentVariable",
            "route",
        }
        if not required <= set(value):
            raise ValueError("integration request is missing required fields")
        for field_name in required:
            if not isinstance(value[field_name], str):
                raise ValueError(f"integration field must be a string: {field_name}")
        target_id = value.get("targetId")
        username = value.get("username")
        enabled = value.get("enabled", True)
        if target_id is not None and not isinstance(target_id, str):
            raise ValueError("integration targetId must be a string")
        if username is not None and not isinstance(username, str):
            raise ValueError("integration username must be a string")
        if not isinstance(enabled, bool):
            raise ValueError("integration enabled must be a boolean")
        route = cast(str, value["route"]).strip()
        normalized_target = target_id.strip() if isinstance(target_id, str) else None
        if normalized_target is not None:
            destination = self._store.destination(normalized_target)
            if destination is None or destination.route != route:
                raise ValueError("integration target is not configured for route")
        integration = InboundIntegration(
            integration_id=cast(str, value["integrationId"]).strip(),
            provider=cast(str, value["provider"]).strip(),
            producer=cast(str, value["producer"]).strip(),
            secret_environment_variable=cast(
                str,
                value["secretEnvironmentVariable"],
            ).strip(),
            route=route,
            target_id=normalized_target,
            username=username.strip() if isinstance(username, str) else None,
            enabled=enabled,
        )
        self._required_integration_store().configure(integration)
        return next(
            item
            for item in self.integrations()
            if item["integrationId"] == integration.integration_id
        )

    def _required_api_key_store(self) -> SqliteProducerApiKeyStore:
        if self._api_keys is None:
            raise ValueError("producer API-key administration is unavailable")
        return self._api_keys

    def _required_integration_store(self) -> SqliteInboundIntegrationStore:
        if self._integrations is None:
            raise ValueError("inbound integration administration is unavailable")
        return self._integrations

    def _router_base_url(self) -> str:
        return NotificationRouterUrl(
            self._environment.get(
                "NOTIFICATION_ROUTER_URL",
                "http://127.0.0.1:8080",
            )
            or "http://127.0.0.1:8080"
        ).value.rstrip("/")

    def add_teams_channel(self, *, route: str, channel_link: str) -> JsonObject:
        """Ensure Team membership and register one channel destination."""
        link = TeamsChannelLink(channel_link)
        expected_tenant = _required_uuid_environment(
            self._environment,
            "TEAMS_NOTIFY_TENANT_ID",
        )
        if link.tenant_id != expected_tenant:
            raise ValueError(
                "Teams channel link tenant does not match configured tenant"
            )
        TeamsWorkflowUrl(_required_environment(self._environment, "TEAMS_WORKFLOW_URL"))
        connection_user = _required_uuid_environment(
            self._environment,
            "TEAMS_CONNECTION_USER_ID",
        )
        token = _teams_notify_app_token(self._environment)
        membership_type, team_membership, channel_membership = (
            _ensure_channel_memberships(
                token,
                link,
                str(connection_user),
            )
        )
        target_id = _admin_target_id(self._store, link)
        self._store.configure_destination(
            StoredDestination(
                target_id=target_id,
                route=route,
                provider="teams-workflow",
                endpoint_environment_variable="TEAMS_WORKFLOW_URL",
                channel_link=link.value,
                enabled=True,
                membership_type=membership_type.value,
            )
        )
        return {
            "targetId": target_id,
            "route": route,
            "channelName": link.channel_name,
            "membershipType": membership_type.value,
            "teamMembership": ("added" if team_membership.added else "already_present"),
            "channelMembership": (
                "added"
                if channel_membership is not None and channel_membership.added
                else "already_present"
                if channel_membership is not None
                else "inherited"
            ),
            "state": "configured",
        }

    def test_destination(self, target_id: str) -> JsonObject:
        """Send one synthetic notification directly to the selected target."""
        destination = self._store.destination(target_id)
        if destination is None or destination.provider != "teams-workflow":
            raise ValueError("Teams destination was not found")
        channel_name = destination.channel_name or target_id
        notification = CanonicalNotification(
            schema_version="1.0",
            event_id=f"admin-test-{uuid4()}",
            route=destination.route,
            title="PyHookKit 테스트 알림",
            body=f"#{channel_name} 채널의 알림 구성이 정상입니다.",
            severity=Severity.INFO,
            metadata={"source": "admin-dashboard"},
        )
        result = self._delivery.deliver(target_id, notification)
        notification_id = self._store.record_direct_delivery(
            "admin-dashboard",
            notification,
            target_id,
            result,
            completed_at=datetime.now(UTC),
        )
        output: JsonObject = {
            "notificationId": notification_id,
            "targetId": target_id,
            "channelName": channel_name,
            "state": result.state.value,
            "attempts": result.attempts,
        }
        if result.error is not None:
            output["errorKind"] = result.error.kind.value
            if result.error.status_code is not None:
                output["statusCode"] = result.error.status_code
        return output


def run_notification_router(
    *,
    arguments: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Configure, inspect, or run the central router."""
    parser = _build_parser()
    parsed = parser.parse_args(arguments)
    active_environment = _runtime_environment(parsed.env_file, environment)
    store = SqliteRouteStore(parsed.database)
    api_keys = SqliteProducerApiKeyStore(parsed.database)
    integrations = SqliteInboundIntegrationStore(parsed.database)

    if parsed.command == "init-db":
        print(f"Initialized router database: {parsed.database}")
        return
    if parsed.command == "bootstrap-teams-app":
        _bootstrap_teams_app(
            parsed,
            store,
            environment_file=RuntimeEnvironmentFile(parsed.env_file),
            environment=active_environment,
        )
        return
    if parsed.command == "add-destination":
        if parsed.ensure_team_membership:
            _ensure_team_membership(parsed, environment=active_environment)
        store.configure_destination(
            StoredDestination(
                target_id=parsed.target_id,
                route=parsed.route,
                provider=parsed.provider,
                endpoint_environment_variable=parsed.endpoint_env,
                channel_link=parsed.channel_link,
                enabled=not parsed.disabled,
            )
        )
        print(f"Configured destination: {parsed.target_id}")
        return
    if parsed.command == "doctor":
        _run_doctor(
            store,
            database=parsed.database,
            environment=active_environment,
        )
        return
    if parsed.command == "list-destinations":
        print(
            json.dumps(
                [
                    {
                        "targetId": destination.target_id,
                        "route": destination.route,
                        "provider": destination.provider,
                        "endpointEnvironmentVariable": (
                            destination.endpoint_environment_variable
                        ),
                        "channelLinkConfigured": destination.channel_link is not None,
                        "tenantId": destination.tenant_id,
                        "teamId": destination.team_id,
                        "channelId": destination.channel_id,
                        "channelName": destination.channel_name,
                        "enabled": destination.enabled,
                    }
                    for destination in store.destinations()
                ],
                indent=2,
            )
        )
        return
    if parsed.command == "issue-api-key":
        if parsed.target_id is not None:
            destination = store.destination(parsed.target_id)
            if destination is None or not destination.enabled:
                raise ValueError("API key target is not configured")
        elif not any(
            destination.route == parsed.route and destination.enabled
            for destination in store.destinations()
        ):
            raise ValueError("API key route is not configured")
        issued = api_keys.issue(
            parsed.producer,
            route=parsed.route,
            target_id=parsed.target_id,
        )
        print(
            json.dumps(
                {
                    "keyId": issued.key_id,
                    "producer": issued.producer,
                    "apiKey": issued.value,
                    "route": issued.route,
                    "targetId": issued.target_id,
                    "createdAt": issued.created_at,
                },
                indent=2,
            )
        )
        return
    if parsed.command == "revoke-api-key":
        if not api_keys.revoke(parsed.key_id):
            raise ValueError("API key was not found or is already revoked")
        print(json.dumps({"keyId": parsed.key_id, "state": "revoked"}))
        return
    if parsed.command == "add-integration":
        if parsed.target_id is not None:
            destination = store.destination(parsed.target_id)
            if destination is None or destination.route != parsed.route:
                raise ValueError("integration target is not configured for route")
        integrations.configure(
            InboundIntegration(
                integration_id=parsed.integration_id,
                provider=parsed.provider,
                producer=parsed.producer,
                secret_environment_variable=parsed.secret_env,
                route=parsed.route,
                target_id=parsed.target_id,
                username=parsed.username,
                enabled=not parsed.disabled,
            )
        )
        print(f"Configured inbound integration: {parsed.integration_id}")
        return
    if parsed.command == "list-integrations":
        print(
            json.dumps(
                [
                    {
                        "integrationId": item.integration_id,
                        "provider": item.provider,
                        "producer": item.producer,
                        "secretEnvironmentVariable": (item.secret_environment_variable),
                        "route": item.route,
                        "targetId": item.target_id,
                        "username": item.username,
                        "enabled": item.enabled,
                        "createdAt": item.created_at,
                        "lastReceivedAt": item.last_received_at,
                    }
                    for item in integrations.integrations()
                ],
                indent=2,
            )
        )
        return
    if parsed.command == "admin":
        if parsed.host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("administrator dashboard must bind to a loopback host")
        RouterAdminRequestHandler.application = RouterAdminHttpApplication(
            SqliteRouterAdminController(
                store,
                active_environment,
                api_keys=api_keys,
                integrations=integrations,
            ),
            AdminAuthenticator(
                _required_environment(active_environment, parsed.admin_token_env)
            ),
        )
        server = ThreadingHTTPServer(
            (parsed.host, parsed.port),
            RouterAdminRequestHandler,
        )
        print(
            f"Router administrator dashboard: http://{parsed.host}:{parsed.port}/admin"
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return

    delivery = ConfiguredNotificationDelivery(store, active_environment)
    router = NotificationRouter(store, delivery)
    if parsed.command == "work-once":
        delivered = router.drain(limit=parsed.limit)
        print(json.dumps({"deliveriesProcessed": delivered}))
        return
    if parsed.command == "serve":
        secrets = _producer_secrets(
            parsed.producer or [],
            environment=active_environment,
        )
        verifiers = (api_keys,)
        if secrets:
            verifiers = (ProducerAuthenticator(secrets), *verifiers)
        application = RouterHttpApplication(
            router,
            CompositeProducerAuthenticator(verifiers),
            provider_webhooks=ProviderWebhookHttpApplication(
                router,
                integrations,
                active_environment,
            ),
        )
        RouterRequestHandler.application = application
        server = ThreadingHTTPServer(
            (parsed.host, parsed.port),
            RouterRequestHandler,
        )
        stop = Event()
        worker = Thread(
            target=NotificationWorker(
                router,
                poll_interval_seconds=parsed.poll_interval,
            ).run,
            args=(stop,),
            name="pyhookkit-notification-worker",
            daemon=True,
        )
        worker.start()
        print(f"Notification router listening on {parsed.host}:{parsed.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            server.server_close()
            worker.join(timeout=parsed.poll_interval + 1)
        return
    raise RuntimeError(f"unsupported router command: {parsed.command}")


def main() -> None:
    """Run with concise CLI errors."""
    try:
        run_notification_router()
    except (
        MicrosoftGraphTokenError,
        RuntimeEnvironmentFileError,
        TeamsGraphMembershipError,
        TeamsNotifyAppBootstrapError,
        ValueError,
    ) as error:
        raise SystemExit(str(error)) from error


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the SQLite-backed PyHookKit notification router.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("pyhookkit-router.sqlite3"),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=_REPOSITORY_ENV_FILE,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db")

    bootstrap = commands.add_parser("bootstrap-teams-app")
    bootstrap.add_argument("--channel-link", required=True)
    bootstrap.add_argument("--connection-user", required=True)
    bootstrap.add_argument("--app-name", default="TeamsNotifyApp")
    bootstrap.add_argument("--route", default="release-notifications")
    bootstrap.add_argument("--target-id")
    bootstrap.add_argument("--endpoint-env", default="TEAMS_WORKFLOW_URL")
    bootstrap.add_argument("--rotate-secret", action="store_true")
    bootstrap.add_argument("--secret-years", type=int, default=1)

    add_destination = commands.add_parser("add-destination")
    add_destination.add_argument("--target-id", required=True)
    add_destination.add_argument("--route", required=True)
    add_destination.add_argument(
        "--provider",
        required=True,
        choices=("slack", "teams-workflow"),
    )
    add_destination.add_argument("--endpoint-env", required=True)
    add_destination.add_argument("--channel-link")
    add_destination.add_argument("--disabled", action="store_true")
    add_destination.add_argument("--ensure-team-membership", action="store_true")
    add_destination.add_argument(
        "--connection-user-env",
        default="TEAMS_CONNECTION_USER_ID",
    )
    add_destination.add_argument(
        "--tenant-id-env",
        default="TEAMS_NOTIFY_TENANT_ID",
    )
    add_destination.add_argument(
        "--graph-token-env",
        default="MICROSOFT_GRAPH_ACCESS_TOKEN",
    )

    commands.add_parser("list-destinations")
    issue_api_key = commands.add_parser("issue-api-key")
    issue_api_key.add_argument("--producer", required=True)
    issue_scope = issue_api_key.add_mutually_exclusive_group(required=True)
    issue_scope.add_argument("--route")
    issue_scope.add_argument("--target-id")

    revoke_api_key = commands.add_parser("revoke-api-key")
    revoke_api_key.add_argument("--key-id", required=True)

    add_integration = commands.add_parser("add-integration")
    add_integration.add_argument("--integration-id", required=True)
    add_integration.add_argument(
        "--provider",
        required=True,
        choices=("github", "gitlab", "azure-devops"),
    )
    add_integration.add_argument("--producer", required=True)
    add_integration.add_argument("--secret-env", required=True)
    add_integration.add_argument("--route", required=True)
    add_integration.add_argument("--target-id")
    add_integration.add_argument("--username")
    add_integration.add_argument("--disabled", action="store_true")
    commands.add_parser("list-integrations")
    commands.add_parser("doctor")

    admin = commands.add_parser("admin")
    admin.add_argument("--host", default="127.0.0.1")
    admin.add_argument("--port", type=int, default=8081)
    admin.add_argument("--admin-token-env", default="PYHOOKKIT_ADMIN_TOKEN")

    work_once = commands.add_parser("work-once")
    work_once.add_argument("--limit", type=int, default=100)

    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument(
        "--producer",
        action="append",
        metavar="NAME=TOKEN_ENV",
    )
    serve.add_argument("--poll-interval", type=float, default=1.0)
    return parser


def _producer_secrets(
    values: list[str],
    *,
    environment: Mapping[str, str],
) -> dict[str, str]:
    secrets: dict[str, str] = {}
    for value in values:
        producer, separator, variable_name = value.partition("=")
        if not separator or not producer or not variable_name:
            raise ValueError("--producer must use NAME=TOKEN_ENV")
        if producer in secrets:
            raise ValueError(f"producer is configured more than once: {producer}")
        secret = environment.get(variable_name, "")
        if not secret:
            raise ValueError(f"producer token variable is empty: {variable_name}")
        secrets[producer] = secret
    return secrets


def _ensure_team_membership(
    parsed: argparse.Namespace,
    *,
    environment: Mapping[str, str],
) -> None:
    if parsed.provider != "teams-workflow" or parsed.channel_link is None:
        raise ValueError(
            "--ensure-team-membership requires a Teams Workflow channel link"
        )
    channel_link = TeamsChannelLink(parsed.channel_link)
    expected_tenant = _required_uuid_environment(
        environment,
        parsed.tenant_id_env,
    )
    if channel_link.tenant_id != expected_tenant:
        raise ValueError("Teams channel link tenant does not match configured tenant")
    connection_user = _required_environment(
        environment,
        parsed.connection_user_env,
    )
    token = _membership_token(
        environment,
        legacy_token_variable=parsed.graph_token_env,
    )
    membership_type, team_result, channel_result = _ensure_channel_memberships(
        token,
        channel_link,
        connection_user,
    )
    team_state = "added" if team_result.added else "already present"
    print(f"Teams connection user Team membership: {team_state}")
    if channel_result is not None:
        channel_state = "added" if channel_result.added else "already present"
        print(
            f"Teams connection user {membership_type.value} channel membership: "
            f"{channel_state}"
        )


def _bootstrap_teams_app(
    parsed: argparse.Namespace,
    store: SqliteRouteStore,
    *,
    environment_file: RuntimeEnvironmentFile,
    environment: Mapping[str, str],
) -> None:
    channel_link = TeamsChannelLink(parsed.channel_link)
    TeamsWorkflowUrl(_required_environment(environment, parsed.endpoint_env))
    bootstrapper = AzureCliTeamsNotifyAppBootstrapper()
    result = bootstrapper.bootstrap(
        channel_link.tenant_id,
        parsed.connection_user,
        app_name=parsed.app_name,
    )
    existing_client_id = environment.get("TEAMS_NOTIFY_CLIENT_ID", "").strip()
    existing_secret = environment.get("TEAMS_NOTIFY_CLIENT_SECRET", "").strip()
    reuse_secret = (
        not parsed.rotate_secret
        and existing_client_id == str(result.client_id)
        and bool(existing_secret)
    )
    created_secret: TeamsNotifyAppSecret | None = None
    if reuse_secret:
        client_secret = existing_secret
    else:
        created_secret = bootstrapper.create_secret(
            result.client_id,
            years=parsed.secret_years,
        )
        client_secret = created_secret.value
    credentials = TeamsNotifyAppCredentials(
        channel_link.tenant_id,
        result.client_id,
        client_secret,
    )
    try:
        token = MicrosoftGraphClientCredentialsTokenProvider(credentials).token()
        environment_file.update(
            {
                "TEAMS_NOTIFY_TENANT_ID": str(channel_link.tenant_id),
                "TEAMS_NOTIFY_CLIENT_ID": str(result.client_id),
                "TEAMS_NOTIFY_CLIENT_SECRET": client_secret,
                "TEAMS_CONNECTION_USER_ID": str(result.connection_user_id),
            }
        )
    except (MicrosoftGraphTokenError, RuntimeEnvironmentFileError):
        if created_secret is not None:
            bootstrapper.delete_secret(result.client_id, created_secret.key_id)
        raise
    membership_type, membership, channel_membership = _ensure_channel_memberships(
        token,
        channel_link,
        str(result.connection_user_id),
    )
    target_id = parsed.target_id or _default_target_id(channel_link)
    store.configure_destination(
        StoredDestination(
            target_id=target_id,
            route=parsed.route,
            provider="teams-workflow",
            endpoint_environment_variable=parsed.endpoint_env,
            channel_link=channel_link.value,
            enabled=True,
            membership_type=membership_type.value,
        )
    )
    app_state = "created" if result.created else "reused"
    membership_state = "added" if membership.added else "already present"
    print(f"TeamsNotifyApp: {app_state}")
    print(f"Teams connection user Team membership: {membership_state}")
    if channel_membership is not None:
        channel_state = "added" if channel_membership.added else "already present"
        print(
            f"Teams connection user {membership_type.value} channel membership: "
            f"{channel_state}"
        )
    print(f"Configured destination: {target_id}")
    print(f"Protected environment updated: {parsed.env_file}")


def _run_doctor(
    store: SqliteRouteStore,
    *,
    database: Path,
    environment: Mapping[str, str],
) -> None:
    TeamsWorkflowUrl(_required_environment(environment, "TEAMS_WORKFLOW_URL"))
    tenant_id = _required_uuid_environment(
        environment,
        "TEAMS_NOTIFY_TENANT_ID",
    )
    user_id = _required_uuid_environment(
        environment,
        "TEAMS_CONNECTION_USER_ID",
    )
    token = _teams_notify_app_token(environment)
    provisioner = TeamsGraphMembershipProvisioner(token)
    channel_provisioner = TeamsGraphChannelMembershipProvisioner(token)
    inspector = TeamsGraphChannelInspector(token)
    destinations = tuple(
        destination
        for destination in store.destinations()
        if destination.provider == "teams-workflow" and destination.enabled
    )
    if not destinations:
        raise ValueError("no enabled Teams Workflow destinations are configured")
    missing: list[str] = []
    for destination in destinations:
        if destination.tenant_id != str(tenant_id) or destination.team_id is None:
            raise ValueError(
                f"Teams destination tenant metadata is invalid: {destination.target_id}"
            )
        if destination.channel_id is None:
            raise ValueError(
                "Teams destination channel metadata is invalid: "
                f"{destination.target_id}"
            )
        membership_type = inspector.membership_type(
            UUID(destination.team_id),
            destination.channel_id,
        )
        if membership_type is TeamsChannelMembershipType.SHARED:
            raise ValueError(
                "Teams destination cannot use a shared channel: "
                f"{destination.target_id}"
            )
        if not provisioner.is_member(UUID(destination.team_id), user_id):
            missing.append(destination.target_id)
        if (
            membership_type is TeamsChannelMembershipType.PRIVATE
            and not channel_provisioner.is_member(
                UUID(destination.team_id),
                destination.channel_id,
                user_id,
            )
        ):
            missing.append(destination.target_id)
    if missing:
        raise ValueError(
            "Teams connection user is not a member for destinations: "
            + ", ".join(sorted(missing))
        )
    if stat.S_IMODE(database.stat().st_mode) != 0o600:
        raise ValueError("router database must use owner-only permissions")
    print(
        json.dumps(
            {
                "state": "healthy",
                "workflowUrl": "valid",
                "graphAppToken": "valid",
                "teamsDestinations": len(destinations),
                "memberships": "verified",
                "databaseMode": "0600",
            },
            indent=2,
        )
    )


def _runtime_environment(
    path: Path,
    provided: Mapping[str, str] | None,
) -> dict[str, str]:
    if provided is not None:
        return dict(provided)
    values = RuntimeEnvironmentFile(path).load()
    values.update({name: value for name, value in os.environ.items() if value})
    return values


def _membership_token(
    environment: Mapping[str, str],
    *,
    legacy_token_variable: str,
) -> MicrosoftGraphAccessToken:
    new_values = (
        "TEAMS_NOTIFY_TENANT_ID",
        "TEAMS_NOTIFY_CLIENT_ID",
        "TEAMS_NOTIFY_CLIENT_SECRET",
    )
    if any(environment.get(name, "").strip() for name in new_values):
        return _teams_notify_app_token(environment)
    return MicrosoftGraphAccessToken(
        _required_environment(environment, legacy_token_variable)
    )


def _teams_notify_app_token(
    environment: Mapping[str, str],
) -> MicrosoftGraphAccessToken:
    credentials = TeamsNotifyAppCredentials(
        _required_uuid_environment(environment, "TEAMS_NOTIFY_TENANT_ID"),
        _required_uuid_environment(environment, "TEAMS_NOTIFY_CLIENT_ID"),
        _required_environment(environment, "TEAMS_NOTIFY_CLIENT_SECRET"),
    )
    return MicrosoftGraphClientCredentialsTokenProvider(credentials).token()


def _ensure_channel_memberships(
    token: MicrosoftGraphAccessToken,
    channel_link: TeamsChannelLink,
    connection_user: str,
) -> tuple[
    TeamsChannelMembershipType,
    TeamMembershipResult,
    TeamMembershipResult | None,
]:
    membership_type = TeamsGraphChannelInspector(token).membership_type(
        channel_link.team_id,
        channel_link.channel_id,
    )
    if membership_type is TeamsChannelMembershipType.SHARED:
        raise ValueError(
            "shared Teams channels are not supported because they can cross "
            "tenant boundaries"
        )
    team_membership = TeamsGraphMembershipProvisioner(token).ensure_member(
        channel_link.team_id,
        connection_user,
    )
    channel_membership = None
    if membership_type is TeamsChannelMembershipType.PRIVATE:
        channel_membership = TeamsGraphChannelMembershipProvisioner(
            token
        ).ensure_member(
            channel_link.team_id,
            channel_link.channel_id,
            team_membership.user_id,
        )
    return membership_type, team_membership, channel_membership


def _default_target_id(channel_link: TeamsChannelLink) -> str:
    slug = _TARGET_SLUG.sub("-", channel_link.channel_name.lower()).strip("-")
    if not slug:
        slug = "channel"
    return f"teams-{slug[:32]}-{str(channel_link.team_id)[:8]}"


def _admin_target_id(
    store: SqliteRouteStore,
    channel_link: TeamsChannelLink,
) -> str:
    destinations = store.destinations()
    for destination in destinations:
        if (
            destination.provider == "teams-workflow"
            and destination.team_id == str(channel_link.team_id)
            and destination.channel_id == channel_link.channel_id
        ):
            return destination.target_id

    slug = _TARGET_SLUG.sub("-", channel_link.channel_name.lower()).strip("-")
    base = f"teams-{slug[:40] or 'channel'}"
    used = {destination.target_id for destination in destinations}
    if base not in used:
        return base
    postfix = 2
    while f"{base}-{postfix}" in used:
        postfix += 1
    return f"{base}-{postfix}"


def _required_environment(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name, "").strip()
    if not value:
        raise ValueError(f"environment variable is required: {name}")
    return value


def _required_uuid_environment(
    environment: Mapping[str, str],
    name: str,
) -> UUID:
    value = _required_environment(environment, name)
    try:
        return UUID(value)
    except ValueError as error:
        raise ValueError(f"environment variable must contain a GUID: {name}") from error


if __name__ == "__main__":
    main()
