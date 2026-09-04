"""Composition root for the SQLite-backed central notification router."""

import argparse
import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from uuid import UUID

from pyhookkit.adapters.inbound.router_http import (
    ProducerAuthenticator,
    RouterHttpApplication,
    RouterRequestHandler,
)
from pyhookkit.adapters.outbound.configured_notification_delivery import (
    ConfiguredNotificationDelivery,
)
from pyhookkit.adapters.outbound.runtime_environment_file import (
    RuntimeEnvironmentFile,
    RuntimeEnvironmentFileError,
)
from pyhookkit.adapters.outbound.sqlite_route_store import (
    SqliteRouteStore,
    StoredDestination,
)
from pyhookkit.adapters.outbound.teams.channel_link import TeamsChannelLink
from pyhookkit.adapters.outbound.teams.entra_app_bootstrap import (
    AzureCliTeamsNotifyAppBootstrapper,
    TeamsNotifyAppBootstrapError,
    TeamsNotifyAppSecret,
)
from pyhookkit.adapters.outbound.teams.graph_membership import (
    MicrosoftGraphAccessToken,
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

_REPOSITORY_ENV_FILE = Path(__file__).resolve().parents[5] / ".env"
_TARGET_SLUG = re.compile(r"[^a-z0-9]+")


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

    delivery = ConfiguredNotificationDelivery(store, active_environment)
    router = NotificationRouter(store, delivery)
    if parsed.command == "work-once":
        delivered = router.drain(limit=parsed.limit)
        print(json.dumps({"deliveriesProcessed": delivered}))
        return
    if parsed.command == "serve":
        secrets = _producer_secrets(
            parsed.producer,
            environment=active_environment,
        )
        application = RouterHttpApplication(
            router,
            ProducerAuthenticator(secrets),
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
    commands.add_parser("doctor")

    work_once = commands.add_parser("work-once")
    work_once.add_argument("--limit", type=int, default=100)

    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument(
        "--producer",
        action="append",
        required=True,
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
    result = TeamsGraphMembershipProvisioner(
        _membership_token(
            environment,
            legacy_token_variable=parsed.graph_token_env,
        )
    ).ensure_member(channel_link.team_id, connection_user)
    state = "added" if result.added else "already present"
    print(f"Teams connection user membership: {state}")


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
    membership = TeamsGraphMembershipProvisioner(token).ensure_member(
        channel_link.team_id,
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
        )
    )
    app_state = "created" if result.created else "reused"
    membership_state = "added" if membership.added else "already present"
    print(f"TeamsNotifyApp: {app_state}")
    print(f"Teams connection user membership: {membership_state}")
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
        if not provisioner.is_member(UUID(destination.team_id), user_id):
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
    values.update(os.environ)
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


def _default_target_id(channel_link: TeamsChannelLink) -> str:
    slug = _TARGET_SLUG.sub("-", channel_link.channel_name.lower()).strip("-")
    if not slug:
        slug = "channel"
    return f"teams-{slug[:32]}-{str(channel_link.team_id)[:8]}"


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
