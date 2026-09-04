"""Azure CLI bootstrap for a visible TeamsNotifyApp registration."""

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Protocol, cast
from uuid import UUID

from pyhookkit.json_types import JsonObject, JsonValue

_GRAPH_APP_ID = UUID("00000003-0000-0000-c000-000000000000")
_MEMBERSHIP_ROLE = "GroupMember.ReadWrite.All"
_APP_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}$")


class TeamsNotifyAppBootstrapError(RuntimeError):
    """TeamsNotifyApp could not be safely created or configured."""


class AzureCliRunner(Protocol):
    """Execute one Azure CLI command and return stdout."""

    def __call__(self, arguments: tuple[str, ...]) -> str:
        """Run Azure CLI without a shell."""
        ...


class SubprocessAzureCliRunner:
    """Non-shell Azure CLI process adapter."""

    def __call__(self, arguments: tuple[str, ...]) -> str:
        try:
            completed = subprocess.run(
                ["az", *arguments],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise TeamsNotifyAppBootstrapError(
                "Azure CLI bootstrap command could not run"
            ) from error
        if completed.returncode != 0:
            operation = " ".join(arguments[:3])
            raise TeamsNotifyAppBootstrapError(
                f"Azure CLI operation failed: {operation}"
            )
        return completed.stdout.strip()


@dataclass(frozen=True, slots=True)
class TeamsNotifyAppBootstrapResult:
    """Non-secret identifiers produced by app bootstrap."""

    application_object_id: UUID
    client_id: UUID
    service_principal_id: UUID
    connection_user_id: UUID
    created: bool


@dataclass(frozen=True, slots=True, repr=False)
class TeamsNotifyAppSecret:
    """A newly created client secret and its removable credential ID."""

    value: str
    key_id: UUID

    def __repr__(self) -> str:
        return f"TeamsNotifyAppSecret(value=<redacted>, key_id={self.key_id!r})"


class AzureCliTeamsNotifyAppBootstrapper:
    """Create or reuse a single-tenant app and grant its Graph app role."""

    def __init__(self, *, run: AzureCliRunner | None = None) -> None:
        self._run = run or SubprocessAzureCliRunner()

    def bootstrap(
        self,
        tenant_id: UUID,
        connection_user: str,
        *,
        app_name: str = "TeamsNotifyApp",
    ) -> TeamsNotifyAppBootstrapResult:
        """Configure an auditable app and resolve the connection user."""
        if _APP_NAME.fullmatch(app_name) is None:
            raise ValueError("TeamsNotifyApp display name is invalid")
        if not connection_user.strip():
            raise ValueError("Teams connection user must not be blank")
        self._verify_tenant(tenant_id)

        applications = self._applications(app_name)
        if len(applications) > 1:
            raise TeamsNotifyAppBootstrapError(
                f"multiple app registrations use the display name: {app_name}"
            )
        created = not applications
        application = self._create_application(app_name) if created else applications[0]
        application_object_id = _uuid_field(application, "id", "application")
        client_id = _uuid_field(application, "appId", "application")
        service_principal_id = self._ensure_service_principal(client_id)
        role_id = self._graph_membership_role_id()
        if not _application_has_role(application, role_id):
            self._run(
                (
                    "ad",
                    "app",
                    "permission",
                    "add",
                    "--id",
                    str(client_id),
                    "--api",
                    str(_GRAPH_APP_ID),
                    "--api-permissions",
                    f"{role_id}=Role",
                    "--only-show-errors",
                )
            )
        self._ensure_admin_consent(service_principal_id, role_id)
        connection_user_id = _uuid_output(
            self._run(
                (
                    "ad",
                    "user",
                    "show",
                    "--id",
                    connection_user,
                    "--query",
                    "id",
                    "-o",
                    "tsv",
                    "--only-show-errors",
                )
            ),
            "Teams connection user",
        )
        return TeamsNotifyAppBootstrapResult(
            application_object_id,
            client_id,
            service_principal_id,
            connection_user_id,
            created,
        )

    def create_secret(
        self,
        client_id: UUID,
        *,
        years: int = 1,
    ) -> TeamsNotifyAppSecret:
        """Create one client secret and return it exactly once."""
        if years < 1 or years > 2:
            raise ValueError("TeamsNotifyApp secret lifetime must be 1 or 2 years")
        before = self._credential_ids(client_id)
        secret = self._run(
            (
                "ad",
                "app",
                "credential",
                "reset",
                "--id",
                str(client_id),
                "--append",
                "--display-name",
                "PyHookKit router",
                "--years",
                str(years),
                "--query",
                "password",
                "-o",
                "tsv",
                "--only-show-errors",
            )
        )
        if len(secret) < 16:
            raise TeamsNotifyAppBootstrapError(
                "Azure CLI returned an invalid TeamsNotifyApp client secret"
            )
        created_ids = self._credential_ids(client_id) - before
        if len(created_ids) != 1:
            raise TeamsNotifyAppBootstrapError(
                "TeamsNotifyApp created credential could not be identified"
            )
        return TeamsNotifyAppSecret(secret, created_ids.pop())

    def delete_secret(self, client_id: UUID, key_id: UUID) -> None:
        """Delete one client credential after a failed bootstrap."""
        self._run(
            (
                "ad",
                "app",
                "credential",
                "delete",
                "--id",
                str(client_id),
                "--key-id",
                str(key_id),
                "--only-show-errors",
            )
        )

    def _verify_tenant(self, tenant_id: UUID) -> None:
        active_tenant = _uuid_output(
            self._run(
                (
                    "account",
                    "get-access-token",
                    "--tenant",
                    str(tenant_id),
                    "--resource-type",
                    "ms-graph",
                    "--query",
                    "tenant",
                    "-o",
                    "tsv",
                    "--only-show-errors",
                )
            ),
            "Azure CLI tenant",
        )
        if active_tenant != tenant_id:
            raise TeamsNotifyAppBootstrapError(
                "Azure CLI token tenant does not match the channel tenant"
            )

    def _applications(self, app_name: str) -> list[JsonObject]:
        output = self._run(
            (
                "ad",
                "app",
                "list",
                "--display-name",
                app_name,
                "-o",
                "json",
                "--only-show-errors",
            )
        )
        values = _json_array(output, "app registration list")
        return [item for item in values if item.get("displayName") == app_name]

    def _create_application(self, app_name: str) -> JsonObject:
        output = self._run(
            (
                "ad",
                "app",
                "create",
                "--display-name",
                app_name,
                "--sign-in-audience",
                "AzureADMyOrg",
                "-o",
                "json",
                "--only-show-errors",
            )
        )
        return _json_object(output, "app registration")

    def _ensure_service_principal(self, client_id: UUID) -> UUID:
        output = self._run(
            (
                "ad",
                "sp",
                "list",
                "--filter",
                f"appId eq '{client_id}'",
                "-o",
                "json",
                "--only-show-errors",
            )
        )
        principals = _json_array(output, "service principal list")
        if len(principals) > 1:
            raise TeamsNotifyAppBootstrapError(
                "multiple service principals exist for TeamsNotifyApp"
            )
        if principals:
            return _uuid_field(
                principals[0],
                "id",
                "TeamsNotifyApp service principal",
            )
        created = _json_object(
            self._run(
                (
                    "ad",
                    "sp",
                    "create",
                    "--id",
                    str(client_id),
                    "-o",
                    "json",
                    "--only-show-errors",
                )
            ),
            "TeamsNotifyApp service principal",
        )
        return _uuid_field(created, "id", "TeamsNotifyApp service principal")

    def _graph_membership_role_id(self) -> UUID:
        graph = _json_object(
            self._run(
                (
                    "ad",
                    "sp",
                    "show",
                    "--id",
                    str(_GRAPH_APP_ID),
                    "-o",
                    "json",
                    "--only-show-errors",
                )
            ),
            "Microsoft Graph service principal",
        )
        raw_roles = graph.get("appRoles")
        if not isinstance(raw_roles, list):
            raise TeamsNotifyAppBootstrapError(
                "Microsoft Graph application roles are unavailable"
            )
        matches: list[UUID] = []
        for raw_role in cast(list[JsonValue], raw_roles):
            if not isinstance(raw_role, dict):
                continue
            allowed = raw_role.get("allowedMemberTypes")
            if (
                raw_role.get("value") == _MEMBERSHIP_ROLE
                and isinstance(allowed, list)
                and "Application" in allowed
            ):
                raw_id = raw_role.get("id")
                if isinstance(raw_id, str):
                    matches.append(_uuid_output(raw_id, _MEMBERSHIP_ROLE))
        if len(matches) != 1:
            raise TeamsNotifyAppBootstrapError(
                "Microsoft Graph membership application role is ambiguous"
            )
        return matches[0]

    def _credential_ids(self, client_id: UUID) -> set[UUID]:
        values = _json_array(
            self._run(
                (
                    "ad",
                    "app",
                    "credential",
                    "list",
                    "--id",
                    str(client_id),
                    "--query",
                    "[].{keyId:keyId}",
                    "-o",
                    "json",
                    "--only-show-errors",
                )
            ),
            "application credential list",
        )
        return {
            _uuid_field(value, "keyId", "application credential") for value in values
        }

    def _ensure_admin_consent(
        self,
        service_principal_id: UUID,
        role_id: UUID,
    ) -> None:
        if self._has_app_role_assignment(service_principal_id, role_id):
            return
        graph_service_principal_id = _uuid_output(
            self._run(
                (
                    "ad",
                    "sp",
                    "show",
                    "--id",
                    str(_GRAPH_APP_ID),
                    "--query",
                    "id",
                    "-o",
                    "tsv",
                    "--only-show-errors",
                )
            ),
            "Microsoft Graph service principal",
        )
        self._run(
            (
                "rest",
                "--method",
                "POST",
                "--url",
                (
                    "https://graph.microsoft.com/v1.0/servicePrincipals/"
                    f"{service_principal_id}/appRoleAssignments"
                ),
                "--headers",
                "Content-Type=application/json",
                "--body",
                json.dumps(
                    {
                        "principalId": str(service_principal_id),
                        "resourceId": str(graph_service_principal_id),
                        "appRoleId": str(role_id),
                    },
                    separators=(",", ":"),
                ),
                "--output",
                "none",
                "--only-show-errors",
            )
        )
        if not self._has_app_role_assignment(service_principal_id, role_id):
            raise TeamsNotifyAppBootstrapError(
                "Microsoft Graph application permission consent was not persisted"
            )

    def _has_app_role_assignment(
        self,
        service_principal_id: UUID,
        role_id: UUID,
    ) -> bool:
        response = _json_object(
            self._run(
                (
                    "rest",
                    "--method",
                    "GET",
                    "--url",
                    (
                        "https://graph.microsoft.com/v1.0/servicePrincipals/"
                        f"{service_principal_id}/appRoleAssignments"
                    ),
                    "--output",
                    "json",
                    "--only-show-errors",
                )
            ),
            "application role assignments",
        )
        raw_values = response.get("value")
        if not isinstance(raw_values, list):
            raise TeamsNotifyAppBootstrapError(
                "application role assignment response is malformed"
            )
        return any(
            isinstance(value, dict) and value.get("appRoleId") == str(role_id)
            for value in cast(list[JsonValue], raw_values)
        )


def _application_has_role(application: JsonObject, role_id: UUID) -> bool:
    raw_access = application.get("requiredResourceAccess")
    if not isinstance(raw_access, list):
        return False
    for raw_resource in cast(list[JsonValue], raw_access):
        if not isinstance(raw_resource, dict):
            continue
        if raw_resource.get("resourceAppId") != str(_GRAPH_APP_ID):
            continue
        raw_access_entries = raw_resource.get("resourceAccess")
        if not isinstance(raw_access_entries, list):
            continue
        for raw_entry in cast(list[JsonValue], raw_access_entries):
            if (
                isinstance(raw_entry, dict)
                and raw_entry.get("id") == str(role_id)
                and raw_entry.get("type") == "Role"
            ):
                return True
    return False


def _json_array(output: str, operation: str) -> list[JsonObject]:
    value = _json_value(output, operation)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise TeamsNotifyAppBootstrapError(
            f"Azure CLI {operation} response must be an array of objects"
        )
    return cast(list[JsonObject], value)


def _json_object(output: str, operation: str) -> JsonObject:
    value = _json_value(output, operation)
    if not isinstance(value, dict):
        raise TeamsNotifyAppBootstrapError(
            f"Azure CLI {operation} response must be an object"
        )
    return cast(JsonObject, value)


def _json_value(output: str, operation: str) -> JsonValue:
    try:
        return cast(JsonValue, json.loads(output))
    except json.JSONDecodeError as error:
        raise TeamsNotifyAppBootstrapError(
            f"Azure CLI {operation} response is not JSON"
        ) from error


def _uuid_field(value: JsonObject, key: str, operation: str) -> UUID:
    raw_value = value.get(key)
    if not isinstance(raw_value, str):
        raise TeamsNotifyAppBootstrapError(
            f"Azure CLI {operation} response is missing {key}"
        )
    return _uuid_output(raw_value, operation)


def _uuid_output(value: str, operation: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as error:
        raise TeamsNotifyAppBootstrapError(
            f"Azure CLI {operation} returned an invalid identifier"
        ) from error
