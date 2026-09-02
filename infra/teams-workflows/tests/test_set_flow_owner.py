from __future__ import annotations

import importlib.util
import json
import unittest
import urllib.request
from pathlib import Path
from types import ModuleType
from typing import cast
from uuid import UUID

SCRIPT = Path(__file__).parents[1] / "bin" / "set-flow-owner.py"
APPLICATION_ID = UUID("11111111-1111-4111-8111-111111111111")
APPLICATION_USER_ID = UUID("22222222-2222-4222-8222-222222222222")
FLOW_ID = UUID("33333333-3333-4333-8333-333333333333")


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("set_flow_owner", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = _load_script()
DataverseClient = MODULE.DataverseClient
FlowOwnershipError = cast(type[RuntimeError], MODULE.FlowOwnershipError)


class FakeTransport:
    def __init__(self, responses: list[tuple[int, object]]) -> None:
        self.responses = responses
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request) -> tuple[int, bytes]:
        self.requests.append(request)
        status, body = self.responses.pop(0)
        return status, b"" if body is None else json.dumps(body).encode()


class FlowOwnerTests(unittest.TestCase):
    def test_assigns_application_user_and_verifies_owner(self) -> None:
        transport = FakeTransport(
            [
                (200, {"value": [{"systemuserid": str(APPLICATION_USER_ID)}]}),
                (204, None),
                (200, {"_ownerid_value": str(APPLICATION_USER_ID)}),
            ]
        )
        client = DataverseClient(
            "https://example.crm.dynamics.com", "token", transport=transport
        )

        application_user_id = client.application_user_id(APPLICATION_ID)
        client.assign_flow(FLOW_ID, application_user_id)
        actual_owner_id = client.flow_owner_id(FLOW_ID)

        self.assertEqual(actual_owner_id, APPLICATION_USER_ID)
        patch = transport.requests[1]
        self.assertEqual(patch.method, "PATCH")
        self.assertEqual(
            json.loads(cast(bytes, patch.data)),
            {"ownerid@odata.bind": f"/systemusers({APPLICATION_USER_ID})"},
        )

    def test_rejects_ambiguous_application_user(self) -> None:
        transport = FakeTransport([(200, {"value": []})])
        client = DataverseClient(
            "https://example.crm.dynamics.com", "token", transport=transport
        )

        with self.assertRaisesRegex(FlowOwnershipError, "exactly one"):
            client.application_user_id(APPLICATION_ID)

    def test_does_not_include_response_body_in_http_error(self) -> None:
        transport = FakeTransport([(403, {"error": "sensitive provider response"})])
        client = DataverseClient(
            "https://example.crm.dynamics.com", "token", transport=transport
        )

        with self.assertRaisesRegex(FlowOwnershipError, "HTTP 403") as raised:
            client.flow_owner_id(FLOW_ID)
        self.assertNotIn("sensitive", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
