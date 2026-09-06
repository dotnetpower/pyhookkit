"""Producer API-key issuance, scoping, and revocation tests."""

import re
from pathlib import Path

import pytest

from pyhookkit.adapters.outbound.sqlite_producer_credentials import (
    SqliteProducerApiKeyStore,
)
from pyhookkit.ports.producer_credentials import (
    ProducerAuthenticationError,
    ProducerAuthorizationError,
)


def _headers(value: str, producer: str = "github") -> dict[str, str]:
    return {
        "authorization": f"Bearer {value}",
        "x-pyhookkit-producer": producer,
    }


def test_api_key_is_revealed_once_and_stored_as_redacted_metadata(
    tmp_path: Path,
) -> None:
    store = SqliteProducerApiKeyStore(tmp_path / "router.sqlite3")

    issued = store.issue("github", target_id="teams-release")
    metadata = store.list_keys()
    principal = store.authenticate(_headers(issued.value))

    assert issued.value.startswith(f"phk_{issued.key_id}_")
    assert re.fullmatch(r"phk_[0-9a-f]{12}_[A-Za-z0-9_-]{43}", issued.value)
    assert issued.value not in repr(metadata)
    assert metadata[0].key_id == issued.key_id
    assert metadata[0].last_used_at is None
    assert principal.producer == "github"
    principal.authorize(route="release-notifications", target_id="teams-release")
    with pytest.raises(ProducerAuthorizationError, match="target"):
        principal.authorize(
            route="release-notifications",
            target_id="teams-security",
        )
    assert store.list_keys()[0].last_used_at is not None


def test_route_scoped_key_and_revocation(tmp_path: Path) -> None:
    store = SqliteProducerApiKeyStore(tmp_path / "router.sqlite3")
    issued = store.issue("gitlab", route="release-notifications")
    principal = store.authenticate(_headers(issued.value, "gitlab"))

    principal.authorize(route="release-notifications", target_id=None)
    with pytest.raises(ProducerAuthorizationError, match="route"):
        principal.authorize(route="security-notifications", target_id=None)

    assert store.revoke(issued.key_id) is True
    assert store.revoke(issued.key_id) is False
    with pytest.raises(ProducerAuthenticationError, match="invalid"):
        store.authenticate(_headers(issued.value, "gitlab"))
    assert store.list_keys()[0].revoked_at is not None


def test_api_key_rejects_invalid_inputs_and_credentials(tmp_path: Path) -> None:
    store = SqliteProducerApiKeyStore(tmp_path / "router.sqlite3")

    with pytest.raises(ValueError, match="producer"):
        store.issue("GitHub", route="release-notifications")
    with pytest.raises(ValueError, match="both"):
        store.issue(
            "github",
            route="release-notifications",
            target_id="teams-release",
        )
    with pytest.raises(ValueError, match="route"):
        store.issue("github", route="Invalid Route")
    with pytest.raises(ValueError, match="target"):
        store.issue("github", target_id="Invalid Target")
    with pytest.raises(ValueError, match="ID"):
        store.revoke("invalid")
    with pytest.raises(ProducerAuthenticationError, match="invalid"):
        store.authenticate({})

    issued = store.issue("github", route="release-notifications")
    with pytest.raises(ProducerAuthenticationError, match="invalid"):
        store.authenticate(_headers(issued.value, "gitlab"))
    with pytest.raises(ProducerAuthenticationError, match="invalid"):
        store.authenticate(_headers(issued.value[:-1] + "A"))
