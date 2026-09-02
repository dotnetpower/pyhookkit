from __future__ import annotations

import importlib.util
import json
import stat
import tempfile
import unittest
import urllib.request
from pathlib import Path
from types import ModuleType
from typing import cast
from uuid import UUID

SCRIPT = Path(__file__).parents[1] / "bin" / "list-team-channels.py"
TEAM_ID = UUID("11111111-1111-4111-8111-111111111111")


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("list_team_channels", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = _load_script()
GraphChannelDirectory = MODULE.GraphChannelDirectory
ChannelInventoryError = cast(type[RuntimeError], MODULE.ChannelInventoryError)
write_private_report = MODULE.write_private_report


class FakeTransport:
    def __init__(self, responses: list[tuple[int, object]]) -> None:
        self.responses = responses
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request) -> tuple[int, bytes]:
        self.requests.append(request)
        status, body = self.responses.pop(0)
        return status, json.dumps(body).encode()


class ChannelDirectoryTests(unittest.TestCase):
    def test_lists_all_channels_across_pages(self) -> None:
        next_link = (
            "https://graph.microsoft.com/v1.0/teams/"
            f"{TEAM_ID}/allChannels?$skiptoken=next"
        )
        transport = FakeTransport(
            [
                (
                    200,
                    {
                        "value": [
                            {
                                "id": "19:general@thread.tacv2",
                                "displayName": "General",
                                "membershipType": "standard",
                            }
                        ],
                        "@odata.nextLink": next_link,
                    },
                ),
                (
                    200,
                    {
                        "value": [
                            {
                                "id": "19:shared@thread.tacv2",
                                "displayName": "Shared",
                                "membershipType": "shared",
                            }
                        ]
                    },
                ),
            ]
        )
        directory = GraphChannelDirectory("token", transport=transport)

        channels = directory.channels(TEAM_ID, include_incoming=True)

        self.assertEqual(
            [item["membershipType"] for item in channels], ["standard", "shared"]
        )
        self.assertIn("/allChannels?", transport.requests[0].full_url)
        self.assertEqual(len(transport.requests), 2)

    def test_rejects_next_link_outside_graph(self) -> None:
        transport = FakeTransport(
            [
                (
                    200,
                    {
                        "value": [],
                        "@odata.nextLink": "https://example.test/token-capture",
                    },
                )
            ]
        )
        directory = GraphChannelDirectory("token", transport=transport)

        with self.assertRaisesRegex(ChannelInventoryError, "unexpected origin"):
            directory.channels(TEAM_ID, include_incoming=False)

    def test_writes_report_with_owner_only_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "channels.json"
            write_private_report(report_path, {"channels": []})

            mode = stat.S_IMODE(report_path.stat().st_mode)
            self.assertEqual(mode, 0o600)


if __name__ == "__main__":
    unittest.main()
