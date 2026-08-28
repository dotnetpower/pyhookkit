"""Resolve committed Teams example assets at the composition boundary."""

import os
from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit

_ASSET_MARKER = "https://assets.pyhookkit.example"


class TeamsAssetConfigurationError(ValueError):
    """The Teams gallery asset base URL is missing or invalid."""


def teams_asset_replacements(
    filenames: Sequence[str],
    *,
    environment: Mapping[str, str] | None = None,
) -> Mapping[str, str]:
    active_environment = os.environ if environment is None else environment
    base_url = active_environment.get("TEAMS_ASSET_BASE_URL", "").strip().rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise TeamsAssetConfigurationError(
            "TEAMS_ASSET_BASE_URL must be an absolute HTTPS URL "
            "without query or fragment"
        )
    return {
        f"{_ASSET_MARKER}/{filename}": f"{base_url}/{filename}"
        for filename in filenames
    }
