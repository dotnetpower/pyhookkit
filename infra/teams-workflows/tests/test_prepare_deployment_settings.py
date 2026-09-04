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
        "EnvironmentVariables": [],
        "ConnectionReferences": [
            {
                "LogicalName": "pyk_Teams",
                "ConnectionId": "",
                "ConnectorId": "/providers/Microsoft.PowerApps/apis/shared_teams",
            }
        ],
    }


class PrepareSettingsTests(unittest.TestCase):
    def test_binds_teams_reference_without_changing_environment_values(self) -> None:
        settings = _settings()

        prepared = prepare_settings(
            settings,
            teams_connection_id="shared-teams-example",
        )

        references = prepared["ConnectionReferences"]
        variables = prepared["EnvironmentVariables"]
        self.assertEqual(references[0]["ConnectionId"], "shared-teams-example")
        self.assertEqual(variables, [])

    def test_rejects_missing_teams_reference(self) -> None:
        settings = _settings()
        settings["ConnectionReferences"] = []

        with self.assertRaisesRegex(DeploymentSettingsError, "exactly one"):
            prepare_settings(
                settings,
                teams_connection_id="shared-teams-example",
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
            )

    def test_rejects_blank_connection_id(self) -> None:
        with self.assertRaisesRegex(DeploymentSettingsError, "must not be blank"):
            prepare_settings(_settings(), teams_connection_id=" ")


if __name__ == "__main__":
    unittest.main()
