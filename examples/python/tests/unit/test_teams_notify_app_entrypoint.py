"""TeamsNotifyApp bootstrap and doctor composition tests."""

import json
from pathlib import Path
from typing import ClassVar
from uuid import UUID

import pytest

import pyhookkit.entrypoints.notification_router as entrypoint
from pyhookkit.adapters.outbound.runtime_environment_file import (
    RuntimeEnvironmentFile,
)
from pyhookkit.adapters.outbound.sqlite_route_store import (
    SqliteRouteStore,
    StoredDestination,
)
from pyhookkit.adapters.outbound.teams.entra_app_bootstrap import (
    TeamsNotifyAppBootstrapResult,
    TeamsNotifyAppSecret,
)
from pyhookkit.adapters.outbound.teams.graph_membership import (
    MicrosoftGraphAccessToken,
    TeamMembershipResult,
)
from pyhookkit.adapters.outbound.teams.graph_token import MicrosoftGraphTokenError

_TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")
_TEAM_ID = UUID("22222222-2222-4222-8222-222222222222")
_CLIENT_ID = UUID("33333333-3333-4333-8333-333333333333")
_APP_OBJECT_ID = UUID("44444444-4444-4444-8444-444444444444")
_SP_ID = UUID("55555555-5555-4555-8555-555555555555")
_USER_ID = UUID("66666666-6666-4666-8666-666666666666")
_CHANNEL_LINK = (
    "https://teams.cloud.microsoft/l/channel/"
    "19%3Aexample-channel%40thread.tacv2/General"
    f"?groupId={_TEAM_ID}&tenantId={_TENANT_ID}"
)
_WORKFLOW_URL = (
    "https://default-example.environment.api.powerplatform.com/"
    "workflows/example/triggers/manual/paths/invoke?sig=synthetic"
)


class StubBootstrapper:
    secret_calls: ClassVar[int] = 0

    def bootstrap(
        self,
        tenant_id: UUID,
        connection_user: str,
        *,
        app_name: str,
    ) -> TeamsNotifyAppBootstrapResult:
        assert tenant_id == _TENANT_ID
        assert connection_user == "svc@example.com"
        assert app_name == "TeamsNotifyApp"
        return TeamsNotifyAppBootstrapResult(
            _APP_OBJECT_ID,
            _CLIENT_ID,
            _SP_ID,
            _USER_ID,
            created=True,
        )

    def create_secret(
        self,
        client_id: UUID,
        *,
        years: int,
    ) -> TeamsNotifyAppSecret:
        assert client_id == _CLIENT_ID
        assert years == 1
        self.__class__.secret_calls += 1
        return TeamsNotifyAppSecret(
            "synthetic-generated-client-secret",
            UUID("77777777-7777-4777-8777-777777777777"),
        )

    def delete_secret(self, client_id: UUID, key_id: UUID) -> None:
        raise AssertionError(f"unexpected secret cleanup: {client_id} {key_id}")


class StubTokenProvider:
    def __init__(self, credentials: object) -> None:
        assert "synthetic-generated-client-secret" not in repr(credentials)

    def token(self) -> MicrosoftGraphAccessToken:
        return MicrosoftGraphAccessToken("synthetic-app-token")


class FailingTokenProvider(StubTokenProvider):
    def token(self) -> MicrosoftGraphAccessToken:
        raise MicrosoftGraphTokenError("synthetic token failure")


class StubMembership:
    ensured: ClassVar[list[tuple[UUID, str]]] = []

    def __init__(self, token: MicrosoftGraphAccessToken) -> None:
        assert token.value == "synthetic-app-token"

    def ensure_member(self, team_id: UUID, user: str) -> TeamMembershipResult:
        self.__class__.ensured.append((team_id, user))
        return TeamMembershipResult(_USER_ID, added=True)

    def is_member(self, team_id: UUID, user_id: UUID) -> bool:
        return team_id == _TEAM_ID and user_id == _USER_ID


def test_bootstrap_writes_env_adds_member_and_registers_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "router.sqlite3"
    env_file = tmp_path / ".env"
    StubBootstrapper.secret_calls = 0
    StubMembership.ensured = []
    monkeypatch.setattr(
        entrypoint,
        "AzureCliTeamsNotifyAppBootstrapper",
        StubBootstrapper,
    )
    monkeypatch.setattr(
        entrypoint,
        "MicrosoftGraphClientCredentialsTokenProvider",
        StubTokenProvider,
    )
    monkeypatch.setattr(
        entrypoint,
        "TeamsGraphMembershipProvisioner",
        StubMembership,
    )

    entrypoint.run_notification_router(
        arguments=[
            "--database",
            str(database),
            "--env-file",
            str(env_file),
            "bootstrap-teams-app",
            "--channel-link",
            _CHANNEL_LINK,
            "--connection-user",
            "svc@example.com",
        ],
        environment={"TEAMS_WORKFLOW_URL": _WORKFLOW_URL},
    )

    output = capsys.readouterr().out
    values = RuntimeEnvironmentFile(env_file).load()
    destination = SqliteRouteStore(database).destination("teams-general-22222222")
    assert "TeamsNotifyApp: created" in output
    assert StubBootstrapper.secret_calls == 1
    assert StubMembership.ensured == [(_TEAM_ID, str(_USER_ID))]
    assert values["TEAMS_NOTIFY_TENANT_ID"] == str(_TENANT_ID)
    assert values["TEAMS_NOTIFY_CLIENT_ID"] == str(_CLIENT_ID)
    assert values["TEAMS_CONNECTION_USER_ID"] == str(_USER_ID)
    assert values["TEAMS_NOTIFY_CLIENT_SECRET"] == ("synthetic-generated-client-secret")
    assert destination is not None


def test_bootstrap_removes_new_secret_when_token_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deleted: list[tuple[UUID, UUID]] = []

    class CleanupBootstrapper(StubBootstrapper):
        def delete_secret(self, client_id: UUID, key_id: UUID) -> None:
            deleted.append((client_id, key_id))

    monkeypatch.setattr(
        entrypoint,
        "AzureCliTeamsNotifyAppBootstrapper",
        CleanupBootstrapper,
    )
    monkeypatch.setattr(
        entrypoint,
        "MicrosoftGraphClientCredentialsTokenProvider",
        FailingTokenProvider,
    )

    with pytest.raises(MicrosoftGraphTokenError, match="synthetic token"):
        entrypoint.run_notification_router(
            arguments=[
                "--database",
                str(tmp_path / "router.sqlite3"),
                "--env-file",
                str(tmp_path / ".env"),
                "bootstrap-teams-app",
                "--channel-link",
                _CHANNEL_LINK,
                "--connection-user",
                "svc@example.com",
            ],
            environment={"TEAMS_WORKFLOW_URL": _WORKFLOW_URL},
        )

    assert deleted == [
        (
            _CLIENT_ID,
            UUID("77777777-7777-4777-8777-777777777777"),
        )
    ]


def test_doctor_verifies_app_token_memberships_and_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "router.sqlite3"
    store = SqliteRouteStore(database)
    store.configure_destination(
        StoredDestination(
            "teams-general",
            "release-notifications",
            "teams-workflow",
            "TEAMS_WORKFLOW_URL",
            _CHANNEL_LINK,
            True,
        )
    )
    monkeypatch.setattr(
        entrypoint,
        "MicrosoftGraphClientCredentialsTokenProvider",
        StubTokenProvider,
    )
    monkeypatch.setattr(
        entrypoint,
        "TeamsGraphMembershipProvisioner",
        StubMembership,
    )

    entrypoint.run_notification_router(
        arguments=["--database", str(database), "doctor"],
        environment={
            "TEAMS_WORKFLOW_URL": _WORKFLOW_URL,
            "TEAMS_NOTIFY_TENANT_ID": str(_TENANT_ID),
            "TEAMS_NOTIFY_CLIENT_ID": str(_CLIENT_ID),
            "TEAMS_NOTIFY_CLIENT_SECRET": "synthetic-generated-client-secret",
            "TEAMS_CONNECTION_USER_ID": str(_USER_ID),
        },
    )

    report = json.loads(capsys.readouterr().out)
    assert report == {
        "state": "healthy",
        "workflowUrl": "valid",
        "graphAppToken": "valid",
        "teamsDestinations": 1,
        "memberships": "verified",
        "databaseMode": "0600",
    }
