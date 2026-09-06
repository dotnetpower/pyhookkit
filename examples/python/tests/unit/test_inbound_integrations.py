"""Provider-native inbound integration persistence tests."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyhookkit.adapters.outbound.sqlite_inbound_integrations import (
    SqliteInboundIntegrationStore,
)
from pyhookkit.ports.inbound_integrations import InboundIntegration


def test_store_configures_lists_and_updates_integration(tmp_path: Path) -> None:
    store = SqliteInboundIntegrationStore(tmp_path / "router.sqlite3")
    integration = InboundIntegration(
        integration_id="github-release",
        provider="github",
        producer="github",
        secret_environment_variable="GITHUB_WEBHOOK_SECRET",
        route="release-notifications",
        target_id="teams-release",
        username=None,
        enabled=True,
    )

    store.configure(integration)
    stored = store.integration("github-release")
    store.mark_received(
        "github-release",
        datetime(2026, 9, 6, 12, 0, tzinfo=UTC),
    )

    assert stored is not None
    assert stored.created_at is not None
    assert stored.target_id == "teams-release"
    assert store.integrations()[0].last_received_at == "2026-09-06T12:00:00+00:00"

    store.configure(
        InboundIntegration(
            integration_id="github-release",
            provider="github",
            producer="github",
            secret_environment_variable="GITHUB_WEBHOOK_SECRET",
            route="release-notifications",
            target_id=None,
            username=None,
            enabled=False,
        )
    )
    updated = store.integration("github-release")
    assert updated is not None
    assert updated.enabled is False
    assert updated.target_id is None
    assert updated.created_at == stored.created_at


def test_store_validates_provider_specific_configuration(tmp_path: Path) -> None:
    store = SqliteInboundIntegrationStore(tmp_path / "router.sqlite3")

    with pytest.raises(ValueError, match="provider"):
        store.configure(
            InboundIntegration(
                "hook",
                "unknown",
                "github",
                "WEBHOOK_SECRET",
                "release-notifications",
                None,
                None,
                True,
            )
        )
    with pytest.raises(ValueError, match="username"):
        store.configure(
            InboundIntegration(
                "azure-build",
                "azure-devops",
                "azure-devops",
                "AZURE_DEVOPS_WEBHOOK_PASSWORD",
                "release-notifications",
                None,
                None,
                True,
            )
        )
    with pytest.raises(ValueError, match="only Azure"):
        store.configure(
            InboundIntegration(
                "github-release",
                "github",
                "github",
                "GITHUB_WEBHOOK_SECRET",
                "release-notifications",
                None,
                "user",
                True,
            )
        )
    assert store.integration("missing") is None
