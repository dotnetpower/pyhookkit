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
from pyhookkit.adapters.outbound.teams.channel_metadata import (
    TeamsChannelMembershipType,
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
from pyhookkit.domain.delivery import DeliveryResult, DeliveryState
from pyhookkit.domain.notification import CanonicalNotification, Severity

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


class StubChannelInspector:
    def __init__(self, token: MicrosoftGraphAccessToken) -> None:
        assert token.value == "synthetic-app-token"

    def membership_type(
        self,
        team_id: UUID,
        channel_id: str,
    ) -> TeamsChannelMembershipType:
        assert team_id
        assert channel_id
        return TeamsChannelMembershipType.STANDARD


class StubPrivateChannelInspector(StubChannelInspector):
    def membership_type(
        self,
        team_id: UUID,
        channel_id: str,
    ) -> TeamsChannelMembershipType:
        assert team_id
        assert channel_id
        return TeamsChannelMembershipType.PRIVATE


class StubChannelMembership:
    ensured: ClassVar[list[tuple[UUID, str, UUID]]] = []

    def __init__(self, token: MicrosoftGraphAccessToken) -> None:
        assert token.value == "synthetic-app-token"

    def ensure_member(
        self,
        team_id: UUID,
        channel_id: str,
        user_id: UUID,
    ) -> TeamMembershipResult:
        self.ensured.append((team_id, channel_id, user_id))
        return TeamMembershipResult(user_id, added=True)

    def is_member(
        self,
        team_id: UUID,
        channel_id: str,
        user_id: UUID,
    ) -> bool:
        return bool(team_id and channel_id and user_id)


@pytest.fixture(autouse=True)
def stub_channel_inspector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        entrypoint,
        "TeamsGraphChannelInspector",
        StubChannelInspector,
    )


class CapturingAdminDelivery:
    deliveries: ClassVar[list[tuple[str, CanonicalNotification]]] = []

    def deliver(
        self,
        target_id: str,
        notification: CanonicalNotification,
    ) -> DeliveryResult:
        self.deliveries.append((target_id, notification))
        return DeliveryResult(DeliveryState.SUCCEEDED, attempts=1)


def test_admin_controller_adds_and_lists_channel_and_activity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "router.sqlite3"
    store = SqliteRouteStore(database)
    StubMembership.ensured = []
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
    controller = entrypoint.SqliteRouterAdminController(
        store,
        {
            "TEAMS_NOTIFY_TENANT_ID": str(_TENANT_ID),
            "TEAMS_NOTIFY_CLIENT_ID": str(_CLIENT_ID),
            "TEAMS_NOTIFY_CLIENT_SECRET": "synthetic-generated-client-secret",
            "TEAMS_CONNECTION_USER_ID": str(_USER_ID),
            "TEAMS_WORKFLOW_URL": _WORKFLOW_URL,
        },
        CapturingAdminDelivery(),
    )

    configured = controller.add_teams_channel(
        route="release-notifications",
        channel_link=_CHANNEL_LINK,
    )
    receipt = store.submit(
        "gitlab",
        CanonicalNotification(
            schema_version="1.0",
            event_id="admin-preview-001",
            route="release-notifications",
            body="Synthetic administration preview",
            severity=Severity.INFO,
        ),
    )
    CapturingAdminDelivery.deliveries = []
    test_result = controller.test_destination("teams-general")

    assert configured["state"] == "configured"
    assert configured["membershipType"] == "standard"
    assert configured["teamMembership"] == "added"
    assert configured["channelMembership"] == "inherited"
    assert configured["targetId"] == "teams-general"
    assert StubMembership.ensured == [(_TEAM_ID, str(_USER_ID))]
    assert controller.destinations()[0]["channelName"] == "General"
    assert controller.destinations()[0]["membershipType"] == "standard"
    assert controller.destinations()[0]["webhookUrl"] == (
        "http://127.0.0.1:8080/v1/destinations/teams-general/notifications"
    )
    activity = controller.notifications()
    assert len(activity) == 2
    assert activity[0]["notificationId"] == test_result["notificationId"]
    assert activity[0]["producer"] == "admin-dashboard"
    assert activity[0]["state"] == "delivered"
    assert activity[1]["notificationId"] == receipt.notification_id
    assert activity[1]["state"] == "queued"
    assert all("payload" not in item for item in activity)
    assert test_result["state"] == "succeeded"
    assert CapturingAdminDelivery.deliveries[0][0] == "teams-general"
    test_notification = CapturingAdminDelivery.deliveries[0][1]
    assert test_notification.title == "PyHookKit 테스트 알림"
    assert test_notification.body == "#General 채널의 알림 구성이 정상입니다."
    with pytest.raises(ValueError, match="not found"):
        controller.test_destination("teams-missing")


def test_admin_controller_adds_numeric_postfix_for_duplicate_channel_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_team_id = UUID("77777777-7777-4777-8777-777777777777")
    other_channel_link = _CHANNEL_LINK.replace(str(_TEAM_ID), str(other_team_id))
    store = SqliteRouteStore(tmp_path / "router.sqlite3")
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
    controller = entrypoint.SqliteRouterAdminController(
        store,
        {
            "TEAMS_NOTIFY_TENANT_ID": str(_TENANT_ID),
            "TEAMS_NOTIFY_CLIENT_ID": str(_CLIENT_ID),
            "TEAMS_NOTIFY_CLIENT_SECRET": "synthetic-generated-client-secret",
            "TEAMS_CONNECTION_USER_ID": str(_USER_ID),
            "TEAMS_WORKFLOW_URL": _WORKFLOW_URL,
        },
    )

    first = controller.add_teams_channel(
        route="release-notifications",
        channel_link=_CHANNEL_LINK,
    )
    duplicate_name = controller.add_teams_channel(
        route="service-notifications",
        channel_link=other_channel_link,
    )
    repeated = controller.add_teams_channel(
        route="updated-notifications",
        channel_link=_CHANNEL_LINK,
    )

    assert first["targetId"] == "teams-general"
    assert duplicate_name["targetId"] == "teams-general-2"
    assert repeated["targetId"] == "teams-general"
    assert len(controller.destinations()) == 2
    assert store.destination("teams-general") == StoredDestination(
        "teams-general",
        "updated-notifications",
        "teams-workflow",
        "TEAMS_WORKFLOW_URL",
        _CHANNEL_LINK,
        True,
        str(_TENANT_ID),
        str(_TEAM_ID),
        "19:example-channel@thread.tacv2",
        "General",
        "standard",
    )


def test_admin_controller_adds_private_channel_membership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SqliteRouteStore(tmp_path / "router.sqlite3")
    StubMembership.ensured = []
    StubChannelMembership.ensured = []
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
    monkeypatch.setattr(
        entrypoint,
        "TeamsGraphChannelInspector",
        StubPrivateChannelInspector,
    )
    monkeypatch.setattr(
        entrypoint,
        "TeamsGraphChannelMembershipProvisioner",
        StubChannelMembership,
    )
    controller = entrypoint.SqliteRouterAdminController(
        store,
        {
            "TEAMS_NOTIFY_TENANT_ID": str(_TENANT_ID),
            "TEAMS_NOTIFY_CLIENT_ID": str(_CLIENT_ID),
            "TEAMS_NOTIFY_CLIENT_SECRET": "synthetic-generated-client-secret",
            "TEAMS_CONNECTION_USER_ID": str(_USER_ID),
            "TEAMS_WORKFLOW_URL": _WORKFLOW_URL,
        },
    )

    result = controller.add_teams_channel(
        route="private-notifications",
        channel_link=_CHANNEL_LINK,
    )

    assert result["membershipType"] == "private"
    assert result["teamMembership"] == "added"
    assert result["channelMembership"] == "added"
    assert StubChannelMembership.ensured == [
        (_TEAM_ID, "19:example-channel@thread.tacv2", _USER_ID)
    ]
    assert controller.destinations()[0]["membershipType"] == "private"
    destination = store.destination("teams-general")
    assert destination is not None
    assert destination.membership_type == "private"


def test_admin_controller_manages_scoped_keys_and_inbound_integrations(
    tmp_path: Path,
) -> None:
    database = tmp_path / "router.sqlite3"
    store = SqliteRouteStore(database)
    store.configure_destination(
        StoredDestination(
            "teams-release",
            "release-notifications",
            "teams-workflow",
            "TEAMS_WORKFLOW_URL",
            _CHANNEL_LINK,
            True,
        )
    )
    api_keys = SqliteProducerApiKeyStore(database)
    integrations = SqliteInboundIntegrationStore(database)
    controller = entrypoint.SqliteRouterAdminController(
        store,
        {
            "NOTIFICATION_ROUTER_URL": "https://notify.example.test",
            "GITHUB_WEBHOOK_SECRET": "synthetic-github-secret",
        },
        CapturingAdminDelivery(),
        api_keys=api_keys,
        integrations=integrations,
    )

    issued = controller.issue_api_key(
        producer="github",
        route=None,
        target_id="teams-release",
    )
    configured = controller.add_integration(
        {
            "integrationId": "github-release",
            "provider": "github",
            "producer": "github",
            "secretEnvironmentVariable": "GITHUB_WEBHOOK_SECRET",
            "route": "release-notifications",
            "targetId": "teams-release",
            "enabled": True,
        }
    )

    assert str(issued["apiKey"]).startswith("phk_")
    assert controller.api_keys()[0]["state"] == "active"
    assert configured["webhookUrl"] == (
        "https://notify.example.test/v1/inbound/github/github-release"
    )
    assert configured["secretConfigured"] is True
    assert controller.revoke_api_key(str(issued["keyId"])) is True
    assert controller.api_keys()[0]["state"] == "revoked"

    with pytest.raises(ValueError, match="target"):
        controller.issue_api_key(
            producer="github",
            route=None,
            target_id="missing",
        )
    with pytest.raises(ValueError, match="route"):
        controller.issue_api_key(
            producer="github",
            route="missing-route",
            target_id=None,
        )
    with pytest.raises(ValueError, match="unsupported fields"):
        controller.add_integration(
            {
                "integrationId": "github-release",
                "provider": "github",
                "producer": "github",
                "secretEnvironmentVariable": "GITHUB_WEBHOOK_SECRET",
                "route": "release-notifications",
                "unexpected": True,
            }
        )


def test_admin_controller_reports_unavailable_integration_stores(
    tmp_path: Path,
) -> None:
    controller = entrypoint.SqliteRouterAdminController(
        SqliteRouteStore(tmp_path / "router.sqlite3"),
        {},
        CapturingAdminDelivery(),
    )

    with pytest.raises(ValueError, match="API-key"):
        controller.api_keys()
    with pytest.raises(ValueError, match="integration administration"):
        controller.integrations()


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
