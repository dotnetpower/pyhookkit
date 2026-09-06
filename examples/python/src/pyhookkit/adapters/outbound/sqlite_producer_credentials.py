"""SQLite-backed producer API-key issuance, verification, and revocation."""

import hashlib
import re
import secrets
import sqlite3
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from hmac import compare_digest
from pathlib import Path
from typing import cast

from pyhookkit.ports.producer_credentials import (
    AuthenticatedProducer,
    ProducerAuthenticationError,
)

_PRODUCER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SCOPE = _PRODUCER
_KEY = re.compile(r"^phk_([0-9a-f]{12})_([A-Za-z0-9_-]{43})$")


@dataclass(frozen=True, slots=True, repr=False)
class IssuedProducerApiKey:
    """One-time producer API-key result whose secret must not be persisted."""

    key_id: str
    producer: str
    value: str
    route: str | None
    target_id: str | None
    created_at: str

    def __repr__(self) -> str:
        return (
            "IssuedProducerApiKey(key_id="
            f"{self.key_id!r}, producer={self.producer!r}, value=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class StoredProducerApiKey:
    """Redacted API-key metadata safe for administration responses."""

    key_id: str
    producer: str
    route: str | None
    target_id: str | None
    created_at: str
    revoked_at: str | None
    last_used_at: str | None


class SqliteProducerApiKeyStore:
    """Manage high-entropy producer credentials without storing raw values."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._initialize()

    def issue(
        self,
        producer: str,
        *,
        route: str | None = None,
        target_id: str | None = None,
    ) -> IssuedProducerApiKey:
        """Issue one scoped API key and return its raw value exactly once."""
        _validate_scope(producer, route=route, target_id=target_id)
        key_id = secrets.token_hex(6)
        value = f"phk_{key_id}_{secrets.token_urlsafe(32)}"
        created_at = _timestamp(datetime.now(UTC))
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO producer_api_keys (
                    key_id, producer, secret_digest, route, target_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    key_id,
                    producer,
                    _digest(value),
                    route,
                    target_id,
                    created_at,
                ),
            )
        return IssuedProducerApiKey(
            key_id,
            producer,
            value,
            route,
            target_id,
            created_at,
        )

    def authenticate(
        self,
        headers: Mapping[str, str],
    ) -> AuthenticatedProducer:
        """Verify one API key and return its scoped producer identity."""
        producer = headers.get("x-pyhookkit-producer", "")
        authorization = headers.get("authorization", "")
        prefix = "Bearer "
        supplied = (
            authorization[len(prefix) :] if authorization.startswith(prefix) else ""
        )
        match = _KEY.fullmatch(supplied)
        if _PRODUCER.fullmatch(producer) is None or match is None:
            raise ProducerAuthenticationError("invalid router credentials")
        key_id = match.group(1)
        now = _timestamp(datetime.now(UTC))
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT producer, secret_digest, route, target_id, revoked_at
                FROM producer_api_keys
                WHERE key_id = ?
                """,
                (key_id,),
            ).fetchone()
            if (
                row is None
                or row["revoked_at"] is not None
                or not compare_digest(cast(str, row["producer"]), producer)
                or not compare_digest(
                    cast(str, row["secret_digest"]), _digest(supplied)
                )
            ):
                raise ProducerAuthenticationError("invalid router credentials")
            connection.execute(
                "UPDATE producer_api_keys SET last_used_at = ? WHERE key_id = ?",
                (now, key_id),
            )
            return AuthenticatedProducer(
                producer=producer,
                route=cast(str | None, row["route"]),
                target_id=cast(str | None, row["target_id"]),
            )

    def list_keys(self) -> tuple[StoredProducerApiKey, ...]:
        """Return redacted metadata for all issued API keys."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT key_id, producer, route, target_id, created_at,
                       revoked_at, last_used_at
                FROM producer_api_keys
                ORDER BY created_at DESC, key_id
                """
            ).fetchall()
        return tuple(
            StoredProducerApiKey(
                key_id=cast(str, row["key_id"]),
                producer=cast(str, row["producer"]),
                route=cast(str | None, row["route"]),
                target_id=cast(str | None, row["target_id"]),
                created_at=cast(str, row["created_at"]),
                revoked_at=cast(str | None, row["revoked_at"]),
                last_used_at=cast(str | None, row["last_used_at"]),
            )
            for row in rows
        )

    def revoke(self, key_id: str) -> bool:
        """Revoke an active API key without revealing whether its secret exists."""
        if re.fullmatch(r"[0-9a-f]{12}", key_id) is None:
            raise ValueError("API key ID is invalid")
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE producer_api_keys
                SET revoked_at = ?
                WHERE key_id = ? AND revoked_at IS NULL
                """,
                (_timestamp(datetime.now(UTC)), key_id),
            )
        return cursor.rowcount == 1

    def _initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS producer_api_keys (
                    key_id TEXT PRIMARY KEY,
                    producer TEXT NOT NULL,
                    secret_digest TEXT NOT NULL,
                    route TEXT,
                    target_id TEXT,
                    created_at TEXT NOT NULL,
                    revoked_at TEXT,
                    last_used_at TEXT,
                    CHECK (route IS NULL OR target_id IS NULL)
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


def _validate_scope(
    producer: str,
    *,
    route: str | None,
    target_id: str | None,
) -> None:
    if _PRODUCER.fullmatch(producer) is None:
        raise ValueError("producer must use lower-case kebab-case")
    if route is not None and _SCOPE.fullmatch(route) is None:
        raise ValueError("API key route must use lower-case kebab-case")
    if target_id is not None and _SCOPE.fullmatch(target_id) is None:
        raise ValueError("API key target ID must use lower-case kebab-case")
    if route is not None and target_id is not None:
        raise ValueError("API key cannot restrict both route and target")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()
