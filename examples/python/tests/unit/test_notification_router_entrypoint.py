"""Central notification router composition root tests."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

import pytest

import pyhookkit.entrypoints.notification_router as entrypoint
from pyhookkit.adapters.outbound.teams.graph_membership import TeamMembershipResult

_CHANNEL_LINK = (
    "https://teams.cloud.microsoft/l/channel/"
    "19%3Aexample-channel%40thread.tacv2/General"
    "?groupId=11111111-1111-4111-8111-111111111111"
    "&tenantId=22222222-2222-4222-8222-222222222222"
)


def test_entrypoint_initializes_configures_lists_and_drains(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "router.sqlite3"
    base = ["--database", str(database)]

    entrypoint.run_notification_router(arguments=[*base, "init-db"])
    assert "Initialized router database" in capsys.readouterr().out

    entrypoint.run_notification_router(
        arguments=[
            *base,
            "add-destination",
            "--target-id",
            "slack-release",
            "--route",
            "release-notifications",
            "--provider",
            "slack",
            "--endpoint-env",
            "SLACK_WEBHOOK_URL",
        ]
    )
    assert "Configured destination" in capsys.readouterr().out

    entrypoint.run_notification_router(arguments=[*base, "list-destinations"])
    destinations = json.loads(capsys.readouterr().out)
    assert destinations == [
        {
            "targetId": "slack-release",
            "route": "release-notifications",
            "provider": "slack",
            "endpointEnvironmentVariable": "SLACK_WEBHOOK_URL",
            "channelLinkConfigured": False,
            "tenantId": None,
            "teamId": None,
            "channelId": None,
            "channelName": None,
            "enabled": True,
        }
    ]

    entrypoint.run_notification_router(
        arguments=[*base, "work-once", "--limit", "2"],
        environment={},
    )
    assert json.loads(capsys.readouterr().out) == {"deliveriesProcessed": 0}


class StubMembershipProvisioner:
    calls: ClassVar[list[tuple[object, str]]] = []

    def __init__(self, token: object) -> None:
        assert "synthetic-graph-token" not in repr(token)

    def ensure_member(self, team_id: object, user: str) -> TeamMembershipResult:
        self.calls.append((team_id, user))
        return TeamMembershipResult(
            user_id=entrypoint.UUID("33333333-3333-4333-8333-333333333333"),
            added=True,
        )

    def is_member(self, team_id: object, user_id: object) -> bool:
        self.calls.append((team_id, str(user_id)))
        return True


def test_entrypoint_ensures_team_membership_before_registration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "router.sqlite3"
    StubMembershipProvisioner.calls = []
    monkeypatch.setattr(
        entrypoint,
        "TeamsGraphMembershipProvisioner",
        StubMembershipProvisioner,
    )

    entrypoint.run_notification_router(
        arguments=[
            "--database",
            str(database),
            "add-destination",
            "--target-id",
            "teams-release",
            "--route",
            "release-notifications",
            "--provider",
            "teams-workflow",
            "--endpoint-env",
            "TEAMS_WORKFLOW_URL",
            "--channel-link",
            _CHANNEL_LINK,
            "--ensure-team-membership",
            "--connection-user-env",
            "TEAMS_CONNECTION_USER",
            "--tenant-id-env",
            "TEAMS_TENANT_ID",
        ],
        environment={
            "TEAMS_CONNECTION_USER": "svc-teams-notification@example.com",
            "TEAMS_TENANT_ID": "22222222-2222-4222-8222-222222222222",
            "MICROSOFT_GRAPH_ACCESS_TOKEN": "synthetic-graph-token",
        },
    )

    output = capsys.readouterr().out
    assert "membership: added" in output
    assert "Configured destination" in output
    assert StubMembershipProvisioner.calls == [
        (
            entrypoint.UUID("11111111-1111-4111-8111-111111111111"),
            "svc-teams-notification@example.com",
        )
    ]


def test_entrypoint_rejects_cross_tenant_membership_registration(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="tenant does not match"):
        entrypoint.run_notification_router(
            arguments=[
                "--database",
                str(tmp_path / "router.sqlite3"),
                "add-destination",
                "--target-id",
                "teams-release",
                "--route",
                "release-notifications",
                "--provider",
                "teams-workflow",
                "--endpoint-env",
                "TEAMS_WORKFLOW_URL",
                "--channel-link",
                _CHANNEL_LINK,
                "--ensure-team-membership",
                "--connection-user-env",
                "TEAMS_CONNECTION_USER",
                "--tenant-id-env",
                "TEAMS_TENANT_ID",
            ],
            environment={
                "TEAMS_CONNECTION_USER": "svc@example.com",
                "TEAMS_TENANT_ID": "44444444-4444-4444-8444-444444444444",
                "MICROSOFT_GRAPH_ACCESS_TOKEN": "synthetic-graph-token",
            },
        )


class StubServer:
    closed: ClassVar[bool] = False

    def __init__(self, address: tuple[str, int], handler: object) -> None:
        assert address == ("127.0.0.1", 8080)
        assert handler is entrypoint.RouterRequestHandler

    def serve_forever(self) -> None:
        raise KeyboardInterrupt

    def server_close(self) -> None:
        self.__class__.closed = True


class StubThread:
    started: ClassVar[bool] = False
    joined: ClassVar[bool] = False

    def __init__(
        self,
        *,
        target: Callable[..., object],
        args: tuple[object, ...],
        name: str,
        daemon: bool,
    ) -> None:
        assert callable(target)
        assert args
        assert name == "pyhookkit-notification-worker"
        assert daemon is True

    def start(self) -> None:
        self.__class__.started = True

    def join(self, timeout: float) -> None:
        assert timeout == 1.01
        self.__class__.joined = True


def test_entrypoint_composes_server_and_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    StubServer.closed = False
    StubThread.started = False
    StubThread.joined = False
    monkeypatch.setattr(entrypoint, "ThreadingHTTPServer", StubServer)
    monkeypatch.setattr(entrypoint, "Thread", StubThread)

    entrypoint.run_notification_router(
        arguments=[
            "--database",
            str(tmp_path / "router.sqlite3"),
            "serve",
            "--producer",
            "gitlab=GITLAB_ROUTER_TOKEN",
            "--poll-interval",
            "0.01",
        ],
        environment={"GITLAB_ROUTER_TOKEN": "synthetic-router-token"},
    )

    assert "listening" in capsys.readouterr().out
    assert StubThread.started is True
    assert StubThread.joined is True
    assert StubServer.closed is True


@pytest.mark.parametrize(
    "value, environment, message",
    [
        ("invalid", {}, "NAME=TOKEN_ENV"),
        ("gitlab=MISSING", {}, "variable is empty"),
    ],
)
def test_entrypoint_rejects_invalid_producer_configuration(
    tmp_path: Path,
    value: str,
    environment: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        entrypoint.run_notification_router(
            arguments=[
                "--database",
                str(tmp_path / "router.sqlite3"),
                "serve",
                "--producer",
                value,
            ],
            environment=environment,
        )
