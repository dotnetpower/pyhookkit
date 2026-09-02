from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from types import ModuleType
from typing import cast

SCRIPT = Path(__file__).parents[1] / "bin" / "prepare-deployment-settings.py"
CHANNEL_LINK = (
    "https://teams.microsoft.com/l/channel/"
    "19%3Aexample-channel%40thread.tacv2/General"
    "?groupId=11111111-1111-4111-8111-111111111111"
    "&tenantId=22222222-2222-4222-8222-222222222222"
)


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prepare_deployment_settings", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = _load_script()
prepare_settings = MODULE.prepare_settings
DeploymentSettingsError = cast(type[ValueError], MODULE.DeploymentSettingsError)


def _settings() -> dict[str, object]:
    return {
        "EnvironmentVariables": [
            {"SchemaName": "pyk_AllowedChannelLinks", "Value": ""},
        ],
        "ConnectionReferences": [
            {
                "LogicalName": "pyk_Teams",
                "ConnectionId": "",
                "ConnectorId": "/providers/Microsoft.PowerApps/apis/shared_teams",
            }
        ],
    }


class PrepareSettingsTests(unittest.TestCase):
    def test_binds_teams_reference_and_channel_allowlist(self) -> None:
        settings = _settings()

        prepared = prepare_settings(
            settings,
            teams_connection_id="shared-teams-example",
            allowed_channel_links_schema_name="pyk_AllowedChannelLinks",
            allowed_channel_links=(CHANNEL_LINK,),
        )

        references = prepared["ConnectionReferences"]
        variables = prepared["EnvironmentVariables"]
        self.assertEqual(references[0]["ConnectionId"], "shared-teams-example")
        self.assertEqual(variables[0]["Value"], json.dumps([CHANNEL_LINK]))

    def test_rejects_missing_teams_reference(self) -> None:
        settings = _settings()
        settings["ConnectionReferences"] = []

        with self.assertRaisesRegex(DeploymentSettingsError, "exactly one"):
            prepare_settings(
                settings,
                teams_connection_id="shared-teams-example",
                allowed_channel_links_schema_name="pyk_AllowedChannelLinks",
                allowed_channel_links=(CHANNEL_LINK,),
            )

    def test_rejects_signed_callback_url(self) -> None:
        settings = _settings()
        variables = cast(list[object], settings["EnvironmentVariables"])
        variables.append(
            {"SchemaName": "pyk_Callback", "Value": "https://example.test/?sig=secret"}
        )

        with self.assertRaisesRegex(DeploymentSettingsError, "signed URL"):
            prepare_settings(
                settings,
                teams_connection_id="shared-teams-example",
                allowed_channel_links_schema_name="pyk_AllowedChannelLinks",
                allowed_channel_links=(CHANNEL_LINK,),
            )

    def test_rejects_invalid_or_duplicate_channel_links(self) -> None:
        for links in (("https://example.test/channel",), (CHANNEL_LINK, CHANNEL_LINK)):
            with self.subTest(links=links), self.assertRaises(DeploymentSettingsError):
                prepare_settings(
                    _settings(),
                    teams_connection_id="shared-teams-example",
                    allowed_channel_links_schema_name="pyk_AllowedChannelLinks",
                    allowed_channel_links=links,
                )


if __name__ == "__main__":
    unittest.main()
