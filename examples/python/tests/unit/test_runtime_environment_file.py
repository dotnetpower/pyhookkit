"""Owner-only runtime environment file tests."""

import stat
from pathlib import Path

import pytest

from pyhookkit.adapters.outbound.runtime_environment_file import (
    RuntimeEnvironmentFile,
    RuntimeEnvironmentFileError,
)


def test_file_updates_selected_values_and_preserves_content(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text(
        '# Existing configuration.\nKEEP="unchanged"\nSECRET="old"\n',
        encoding="utf-8",
    )
    environment = RuntimeEnvironmentFile(path)

    environment.update(
        {
            "SECRET": 'new"value',
            "TEAMS_NOTIFY_CLIENT_ID": "11111111-1111-4111-8111-111111111111",
        }
    )

    content = path.read_text(encoding="utf-8")
    assert '# Existing configuration.\nKEEP="unchanged"' in content
    assert 'SECRET="new\\"value"' in content
    assert "TeamsNotifyApp bootstrap configuration" in content
    assert environment.load() == {
        "KEEP": "unchanged",
        "SECRET": 'new"value',
        "TEAMS_NOTIFY_CLIENT_ID": "11111111-1111-4111-8111-111111111111",
    }
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_file_creates_missing_parent_and_owner_only_file(tmp_path: Path) -> None:
    path = tmp_path / "configuration" / ".env"

    RuntimeEnvironmentFile(path).update({"TOKEN": "synthetic-token"})

    assert path.read_text(encoding="utf-8").endswith('TOKEN="synthetic-token"\n')
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.parametrize(
    "content, message",
    [
        ("export TOKEN=value\n", "invalid environment assignment"),
        ("TOKEN=one\nTOKEN=two\n", "duplicate environment variable"),
        ('TOKEN="unterminated\n', "invalid environment value"),
        ("TOKEN=two words\n", "must be quoted"),
    ],
)
def test_file_rejects_malformed_content(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    path = tmp_path / ".env"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(RuntimeEnvironmentFileError, match=message):
        RuntimeEnvironmentFile(path).load()


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"invalid": "value"},
        {"TOKEN": ""},
        {"TOKEN": "line\nbreak"},
    ],
)
def test_file_rejects_unsafe_updates(
    tmp_path: Path,
    values: dict[str, str],
) -> None:
    with pytest.raises(RuntimeEnvironmentFileError):
        RuntimeEnvironmentFile(tmp_path / ".env").update(values)
