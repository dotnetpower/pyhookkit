"""Owner-only runtime environment configuration storage."""

import os
import re
import shlex
import tempfile
from collections.abc import Mapping
from pathlib import Path

_ASSIGNMENT = re.compile(r"^(?P<name>[A-Z][A-Z0-9_]*)=(?P<value>.*)$")


class RuntimeEnvironmentFileError(ValueError):
    """A runtime environment file is malformed or unsafe."""


class RuntimeEnvironmentFile:
    """Read and atomically update a simple dotenv file without evaluation."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, str]:
        """Load literal assignments without shell expansion."""
        if not self._path.exists():
            return {}
        values: dict[str, str] = {}
        for line_number, raw_line in enumerate(
            self._path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = _ASSIGNMENT.fullmatch(line)
            if match is None:
                raise RuntimeEnvironmentFileError(
                    f"invalid environment assignment on line {line_number}"
                )
            name = match.group("name")
            if name in values:
                raise RuntimeEnvironmentFileError(
                    f"duplicate environment variable: {name}"
                )
            values[name] = _literal_value(
                match.group("value"),
                line_number=line_number,
            )
        return values

    def update(self, values: Mapping[str, str]) -> None:
        """Replace selected assignments and preserve unrelated content."""
        if not values:
            raise RuntimeEnvironmentFileError(
                "environment update must contain at least one value"
            )
        normalized = {
            _variable_name(name): _safe_value(name, value)
            for name, value in values.items()
        }
        existing_lines = (
            self._path.read_text(encoding="utf-8").splitlines()
            if self._path.exists()
            else []
        )
        output: list[str] = []
        replaced: set[str] = set()
        seen: set[str] = set()
        for line_number, line in enumerate(existing_lines, start=1):
            match = _ASSIGNMENT.fullmatch(line.strip())
            if match is None:
                output.append(line)
                continue
            name = match.group("name")
            if name in seen:
                raise RuntimeEnvironmentFileError(
                    f"duplicate environment variable on line {line_number}: {name}"
                )
            seen.add(name)
            if name in normalized:
                output.append(f'{name}="{_escaped(normalized[name])}"')
                replaced.add(name)
            else:
                output.append(line)

        missing = sorted(normalized.keys() - replaced)
        if missing:
            if output and output[-1]:
                output.append("")
            output.append("# TeamsNotifyApp bootstrap configuration.")
            output.extend(f'{name}="{_escaped(normalized[name])}"' for name in missing)

        self._write("\n".join(output) + "\n")

    def _write(self, content: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self._path.name}.",
            dir=self._path.parent,
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
                destination.write(content)
                destination.flush()
                os.fsync(destination.fileno())
            os.replace(temporary_path, self._path)
            self._path.chmod(0o600)
        finally:
            temporary_path.unlink(missing_ok=True)


def _literal_value(raw_value: str, *, line_number: int) -> str:
    try:
        parts = shlex.split(raw_value, comments=False, posix=True)
    except ValueError as error:
        raise RuntimeEnvironmentFileError(
            f"invalid environment value on line {line_number}"
        ) from error
    if len(parts) != 1:
        raise RuntimeEnvironmentFileError(
            f"environment value on line {line_number} must be quoted"
        )
    return parts[0]


def _variable_name(name: str) -> str:
    if _ASSIGNMENT.fullmatch(f"{name}=") is None:
        raise RuntimeEnvironmentFileError(f"invalid environment variable name: {name}")
    return name


def _safe_value(name: str, value: str) -> str:
    if not value:
        raise RuntimeEnvironmentFileError(
            f"environment variable must not be blank: {name}"
        )
    if "\n" in value or "\r" in value or "\0" in value:
        raise RuntimeEnvironmentFileError(
            f"environment variable contains unsafe characters: {name}"
        )
    return value


def _escaped(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
