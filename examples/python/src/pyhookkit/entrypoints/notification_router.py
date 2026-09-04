"""Composition root for the SQLite-backed central notification router."""

import argparse
import json
import os
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
from pyhookkit.adapters.outbound.sqlite_route_store import (
    SqliteRouteStore,
    StoredDestination,
)
from pyhookkit.adapters.outbound.teams.channel_link import TeamsChannelLink
from pyhookkit.adapters.outbound.teams.graph_membership import (
    MicrosoftGraphAccessToken,
    TeamsGraphMembershipProvisioner,
)
from pyhookkit.application.notification_router import NotificationRouter
from pyhookkit.application.notification_worker import NotificationWorker


def run_notification_router(
    *,
    arguments: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Configure, inspect, or run the central router."""
    parser = _build_parser()
    parsed = parser.parse_args(arguments)
    active_environment = os.environ if environment is None else environment
    store = SqliteRouteStore(parsed.database)

    if parsed.command == "init-db":
        print(f"Initialized router database: {parsed.database}")
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
    except ValueError as error:
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
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db")

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
        default="TEAMS_CONNECTION_USER",
    )
    add_destination.add_argument(
        "--tenant-id-env",
        default="TEAMS_TENANT_ID",
    )
    add_destination.add_argument(
        "--graph-token-env",
        default="MICROSOFT_GRAPH_ACCESS_TOKEN",
    )

    commands.add_parser("list-destinations")

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
    graph_token = _required_environment(
        environment,
        parsed.graph_token_env,
    )
    result = TeamsGraphMembershipProvisioner(
        MicrosoftGraphAccessToken(graph_token)
    ).ensure_member(channel_link.team_id, connection_user)
    state = "added" if result.added else "already present"
    print(f"Teams connection user membership: {state}")


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
