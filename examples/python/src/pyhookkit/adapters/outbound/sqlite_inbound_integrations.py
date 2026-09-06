"""SQLite configuration for provider-native inbound webhook integrations."""

import re
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pyhookkit.ports.inbound_integrations import InboundIntegration

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ENVIRONMENT_VARIABLE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_PROVIDERS = frozenset({"github", "gitlab", "azure-devops"})


class SqliteInboundIntegrationStore:
    """Persist provider webhook routing without storing authentication secrets."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._initialize()

    def configure(self, integration: InboundIntegration) -> None:
        """Create or replace one provider-native inbound integration."""
        _validate(integration)
        created_at = integration.created_at or datetime.now(UTC).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO inbound_integrations (
                    integration_id, provider, producer,
                    secret_environment_variable, route, target_id, username,
                    enabled, created_at, last_received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(integration_id) DO UPDATE SET
                    provider = excluded.provider,
                    producer = excluded.producer,
                    secret_environment_variable = excluded.secret_environment_variable,
                    route = excluded.route,
                    target_id = excluded.target_id,
                    username = excluded.username,
                    enabled = excluded.enabled
                """,
                (
                    integration.integration_id,
                    integration.provider,
                    integration.producer,
                    integration.secret_environment_variable,
                    integration.route,
                    integration.target_id,
                    integration.username,
                    int(integration.enabled),
                    created_at,
                    integration.last_received_at,
                ),
            )

    def integration(self, integration_id: str) -> InboundIntegration | None:
        """Read one integration without resolving its secret."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT integration_id, provider, producer,
                       secret_environment_variable, route, target_id, username,
                       enabled, created_at, last_received_at
                FROM inbound_integrations
                WHERE integration_id = ?
                """,
                (integration_id,),
            ).fetchone()
        return _from_row(row) if row is not None else None

    def integrations(self) -> tuple[InboundIntegration, ...]:
        """List redacted integration metadata."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT integration_id, provider, producer,
                       secret_environment_variable, route, target_id, username,
                       enabled, created_at, last_received_at
                FROM inbound_integrations
                ORDER BY provider, integration_id
                """
            ).fetchall()
        return tuple(_from_row(row) for row in rows)

    def mark_received(self, integration_id: str, received_at: datetime) -> None:
        """Record successful authenticated receipt without retaining its payload."""
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE inbound_integrations
                SET last_received_at = ?
                WHERE integration_id = ?
                """,
                (received_at.astimezone(UTC).isoformat(), integration_id),
            )

    def _initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inbound_integrations (
                    integration_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    producer TEXT NOT NULL,
                    secret_environment_variable TEXT NOT NULL,
                    route TEXT,
                    target_id TEXT,
                    username TEXT,
                    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
                    created_at TEXT NOT NULL,
                    last_received_at TEXT,
                    CHECK (route IS NOT NULL)
                )
                """
            )
        self._path.chmod(0o600)

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


def _validate(integration: InboundIntegration) -> None:
    for label, value in (
        ("integration ID", integration.integration_id),
        ("producer", integration.producer),
    ):
        if _ID.fullmatch(value) is None:
            raise ValueError(f"{label} must use lower-case kebab-case")
    if integration.provider not in _PROVIDERS:
        raise ValueError("inbound provider must be github, gitlab, or azure-devops")
    if _ENVIRONMENT_VARIABLE.fullmatch(integration.secret_environment_variable) is None:
        raise ValueError("inbound secret environment variable name is invalid")
    if _ID.fullmatch(integration.route) is None:
        raise ValueError("inbound route must use lower-case kebab-case")
    if (
        integration.target_id is not None
        and _ID.fullmatch(integration.target_id) is None
    ):
        raise ValueError("inbound target ID must use lower-case kebab-case")
    if integration.provider == "azure-devops" and not integration.username:
        raise ValueError("Azure DevOps inbound integration requires a username")
    if integration.provider != "azure-devops" and integration.username is not None:
        raise ValueError("only Azure DevOps inbound integrations use a username")


def _from_row(row: sqlite3.Row) -> InboundIntegration:
    return InboundIntegration(
        integration_id=cast(str, row["integration_id"]),
        provider=cast(str, row["provider"]),
        producer=cast(str, row["producer"]),
        secret_environment_variable=cast(str, row["secret_environment_variable"]),
        route=cast(str, row["route"]),
        target_id=cast(str | None, row["target_id"]),
        username=cast(str | None, row["username"]),
        enabled=bool(row["enabled"]),
        created_at=cast(str, row["created_at"]),
        last_received_at=cast(str | None, row["last_received_at"]),
    )
