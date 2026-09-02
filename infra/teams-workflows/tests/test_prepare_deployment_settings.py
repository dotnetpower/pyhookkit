from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType
from typing import cast

SCRIPT = Path(__file__).parents[1] / "bin" / "prepare-deployment-settings.py"


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
            {"SchemaName": "pyk_TeamId", "Value": ""},
            {"SchemaName": "pyk_ChannelId", "Value": ""},
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
    def test_binds_exact_teams_reference_and_destination(self) -> None:
        settings = _settings()

        prepared = prepare_settings(
            settings,
            teams_connection_id="shared-teams-example",
            team_schema_name="pyk_TeamId",
            team_id="11111111-1111-4111-8111-111111111111",
            channel_schema_name="pyk_ChannelId",
            channel_id="19:example@thread.tacv2",
        )

        references = prepared["ConnectionReferences"]
        variables = prepared["EnvironmentVariables"]
        self.assertEqual(references[0]["ConnectionId"], "shared-teams-example")
        self.assertEqual(variables[0]["Value"], "11111111-1111-4111-8111-111111111111")
        self.assertEqual(variables[1]["Value"], "19:example@thread.tacv2")

    def test_rejects_missing_teams_reference(self) -> None:
        settings = _settings()
        settings["ConnectionReferences"] = []

        with self.assertRaisesRegex(DeploymentSettingsError, "exactly one"):
            prepare_settings(
                settings,
                teams_connection_id="shared-teams-example",
                team_schema_name="pyk_TeamId",
                team_id="11111111-1111-4111-8111-111111111111",
                channel_schema_name="pyk_ChannelId",
                channel_id="19:example@thread.tacv2",
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
                team_schema_name="pyk_TeamId",
                team_id="11111111-1111-4111-8111-111111111111",
                channel_schema_name="pyk_ChannelId",
                channel_id="19:example@thread.tacv2",
            )


if __name__ == "__main__":
    unittest.main()
