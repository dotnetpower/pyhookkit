"""Azure CLI TeamsNotifyApp bootstrap tests."""

import json
from uuid import UUID

import pytest

from pyhookkit.adapters.outbound.teams.entra_app_bootstrap import (
    AzureCliTeamsNotifyAppBootstrapper,
    TeamsNotifyAppBootstrapError,
)

_TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")
_APP_OBJECT_ID = UUID("22222222-2222-4222-8222-222222222222")
_CLIENT_ID = UUID("33333333-3333-4333-8333-333333333333")
_SP_ID = UUID("44444444-4444-4444-8444-444444444444")
_USER_ID = UUID("55555555-5555-4555-8555-555555555555")
_ROLE_ID = UUID("66666666-6666-4666-8666-666666666666")
_CREDENTIAL_ID = UUID("77777777-7777-4777-8777-777777777777")


class FakeAzureCli:
    def __init__(self, *, existing: bool) -> None:
        self.existing = existing
        self.calls: list[tuple[str, ...]] = []
        self.assignment_created = existing
        self.credentials: set[UUID] = set()

    def __call__(self, arguments: tuple[str, ...]) -> str:
        self.calls.append(arguments)
        operation = arguments[:3]
        if operation == ("account", "get-access-token", "--tenant"):
            return str(_TENANT_ID)
        if operation == ("ad", "app", "list"):
            if not self.existing:
                return "[]"
            return json.dumps([_application(include_role=True)])
        if operation == ("ad", "app", "create"):
            return json.dumps(_application(include_role=False))
        if operation == ("ad", "sp", "list"):
            return json.dumps([{"id": str(_SP_ID)}] if self.existing else [])
        if operation == ("ad", "sp", "create"):
            return json.dumps({"id": str(_SP_ID)})
        if operation == ("ad", "sp", "show"):
            if "--query" in arguments:
                return str(_SP_ID)
            return json.dumps(
                {
                    "appRoles": [
                        {
                            "id": str(_ROLE_ID),
                            "value": "GroupMember.ReadWrite.All",
                            "allowedMemberTypes": ["Application"],
                        }
                    ]
                }
            )
        if operation == ("ad", "app", "permission"):
            return ""
        if operation[0] == "rest":
            if "GET" in arguments:
                assignments = (
                    [{"appRoleId": str(_ROLE_ID)}] if self.assignment_created else []
                )
                return json.dumps({"value": assignments})
            self.assignment_created = True
            return ""
        if operation == ("ad", "user", "show"):
            return str(_USER_ID)
        if operation == ("ad", "app", "credential"):
            action = arguments[3]
            if action == "list":
                return json.dumps(
                    [{"keyId": str(key_id)} for key_id in self.credentials]
                )
            if action == "delete":
                key_index = arguments.index("--key-id") + 1
                self.credentials.remove(UUID(arguments[key_index]))
                return ""
            self.credentials.add(_CREDENTIAL_ID)
            return "synthetic-generated-client-secret"
        raise AssertionError(f"unexpected Azure CLI call: {arguments}")


def _application(*, include_role: bool) -> dict[str, object]:
    access: list[object] = []
    if include_role:
        access.append(
            {
                "resourceAppId": "00000003-0000-0000-c000-000000000000",
                "resourceAccess": [{"id": str(_ROLE_ID), "type": "Role"}],
            }
        )
    return {
        "id": str(_APP_OBJECT_ID),
        "appId": str(_CLIENT_ID),
        "displayName": "TeamsNotifyApp",
        "requiredResourceAccess": access,
    }


def test_bootstrap_creates_app_sp_permission_and_resolves_user() -> None:
    cli = FakeAzureCli(existing=False)

    result = AzureCliTeamsNotifyAppBootstrapper(run=cli).bootstrap(
        _TENANT_ID,
        "svc-teams-notification@example.com",
    )

    assert result.created is True
    assert result.application_object_id == _APP_OBJECT_ID
    assert result.client_id == _CLIENT_ID
    assert result.service_principal_id == _SP_ID
    assert result.connection_user_id == _USER_ID
    assert any(call[:4] == ("ad", "app", "permission", "add") for call in cli.calls)
    assert any(call[0] == "rest" and "POST" in call for call in cli.calls)


def test_bootstrap_reuses_existing_app_and_permission() -> None:
    cli = FakeAzureCli(existing=True)

    result = AzureCliTeamsNotifyAppBootstrapper(run=cli).bootstrap(
        _TENANT_ID,
        str(_USER_ID),
    )

    assert result.created is False
    assert not any(call[:4] == ("ad", "app", "permission", "add") for call in cli.calls)
    assert not any(call[:3] == ("ad", "sp", "create") for call in cli.calls)


def test_bootstrap_creates_redacted_secret() -> None:
    cli = FakeAzureCli(existing=True)
    bootstrapper = AzureCliTeamsNotifyAppBootstrapper(run=cli)

    secret = bootstrapper.create_secret(_CLIENT_ID)

    assert secret.value == "synthetic-generated-client-secret"
    assert secret.key_id == _CREDENTIAL_ID
    assert "synthetic-generated-client-secret" not in repr(secret)

    bootstrapper.delete_secret(_CLIENT_ID, secret.key_id)
    assert _CREDENTIAL_ID not in cli.credentials


@pytest.mark.parametrize(
    ("app_name", "user"),
    [
        ("invalid/name", "svc@example.com"),
        ("TeamsNotifyApp", " "),
    ],
)
def test_bootstrap_rejects_invalid_input(app_name: str, user: str) -> None:
    with pytest.raises(ValueError):
        AzureCliTeamsNotifyAppBootstrapper(run=FakeAzureCli(existing=False)).bootstrap(
            _TENANT_ID, user, app_name=app_name
        )


def test_bootstrap_rejects_duplicate_app_names() -> None:
    class DuplicateApps(FakeAzureCli):
        def __call__(self, arguments: tuple[str, ...]) -> str:
            if arguments[:3] == ("ad", "app", "list"):
                return json.dumps(
                    [
                        _application(include_role=True),
                        _application(include_role=True),
                    ]
                )
            return super().__call__(arguments)

    with pytest.raises(TeamsNotifyAppBootstrapError, match="multiple app"):
        AzureCliTeamsNotifyAppBootstrapper(run=DuplicateApps(existing=True)).bootstrap(
            _TENANT_ID, str(_USER_ID)
        )


def test_secret_rejects_invalid_lifetime() -> None:
    with pytest.raises(ValueError, match="lifetime"):
        AzureCliTeamsNotifyAppBootstrapper(
            run=FakeAzureCli(existing=True)
        ).create_secret(_CLIENT_ID, years=3)
