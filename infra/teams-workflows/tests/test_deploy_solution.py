from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "bin" / "deploy-solution.sh"
TEAM_ID = "11111111-1111-4111-8111-111111111111"


class DeploySolutionTests(unittest.TestCase):
    def test_packs_prepares_and_imports_solution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            solution = root / "solution"
            solution.mkdir()
            solution_zip = root / "output" / "solution.zip"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            pac_log = root / "pac.log"
            fake_pac = fake_bin / "pac"
            fake_pac.write_text(_fake_pac(), encoding="utf-8")
            fake_pac.chmod(fake_pac.stat().st_mode | stat.S_IXUSR)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
            environment["PAC_LOG"] = str(pac_log)

            completed = subprocess.run(
                [
                    "bash",
                    str(SCRIPT),
                    "--solution-folder",
                    str(solution),
                    "--solution-zip",
                    str(solution_zip),
                    "--package-type",
                    "Managed",
                    "--environment",
                    "https://example.crm.dynamics.com",
                    "--teams-connection-id",
                    "shared-teams-example",
                    "--team-schema-name",
                    "pyk_TeamId",
                    "--team-id",
                    TEAM_ID,
                    "--channel-schema-name",
                    "pyk_ChannelId",
                    "--channel-id",
                    "19:example@thread.tacv2",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("deployment verified", completed.stdout)
            calls = pac_log.read_text(encoding="utf-8")
            self.assertIn("solution pack", calls)
            self.assertIn("solution create-settings", calls)
            self.assertIn("solution import", calls)
            self.assertIn("--settings-file", calls)


def _fake_pac() -> str:
    settings = json.dumps(
        {
            "EnvironmentVariables": [
                {"SchemaName": "pyk_TeamId", "Value": ""},
                {"SchemaName": "pyk_ChannelId", "Value": ""},
            ],
            "ConnectionReferences": [
                {
                    "LogicalName": "pyk_Teams",
                    "ConnectionId": "",
                    "ConnectorId": ("/providers/Microsoft.PowerApps/apis/shared_teams"),
                }
            ],
        }
    )
    return textwrap.dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        printf '%s\\n' "$*" >> "$PAC_LOG"
        if [[ "${{1:-}} ${{2:-}}" == "solution pack" ]]; then
          while (($# > 0)); do
            if [[ "$1" == "--zipfile" ]]; then
              mkdir -p "$(dirname "$2")"
              : > "$2"
              break
            fi
            shift
          done
        fi
        if [[ "${{1:-}} ${{2:-}}" == "solution create-settings" ]]; then
          while (($# > 0)); do
            if [[ "$1" == "--settings-file" ]]; then
              printf '%s\\n' '{settings}' > "$2"
              break
            fi
            shift
          done
        fi
        """
    )


if __name__ == "__main__":
    unittest.main()
