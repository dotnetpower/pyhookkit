#!/usr/bin/env python3
"""Assign and verify a solution-aware cloud flow's application-user owner."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import cast
from uuid import UUID

type JsonValue = (
    bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None
)
type Transport = Callable[[urllib.request.Request], tuple[int, bytes]]


class FlowOwnershipError(RuntimeError):
    """Raised when flow ownership cannot be changed or verified."""


class DataverseClient:
    """Use the narrow Dataverse surface needed for cloud-flow ownership."""

    def __init__(
        self,
        environment_url: str,
        access_token: str,
        *,
        transport: Transport | None = None,
    ) -> None:
        parsed = urllib.parse.urlsplit(environment_url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.path not in ("", "/")
        ):
            raise FlowOwnershipError(
                "environment URL must be an HTTPS Dataverse origin"
            )
        if not access_token:
            raise FlowOwnershipError("Dataverse access token must not be blank")
        self._api_url = f"{environment_url.rstrip('/')}/api/data/v9.2"
        self._access_token = access_token
        self._transport = transport or _send

    def application_user_id(self, application_id: UUID) -> UUID:
        query = urllib.parse.urlencode(
            {
                "$select": "systemuserid",
                "$filter": (
                    f"applicationid eq {application_id} and isdisabled eq false"
                ),
            }
        )
        response = self._request("GET", f"systemusers?{query}")
        values = response.get("value")
        if not isinstance(values, list) or len(values) != 1:
            raise FlowOwnershipError(
                "expected exactly one enabled Dataverse application user"
            )
        item = values[0]
        if not isinstance(item, dict):
            raise FlowOwnershipError("application-user response is malformed")
        application_user_id = item.get("systemuserid")
        if not isinstance(application_user_id, str):
            raise FlowOwnershipError("application-user response is malformed")
        return UUID(application_user_id)

    def assign_flow(self, flow_id: UUID, application_user_id: UUID) -> None:
        self._request(
            "PATCH",
            f"workflows({flow_id})",
            {"ownerid@odata.bind": f"/systemusers({application_user_id})"},
            expected_status=204,
        )

    def flow_owner_id(self, flow_id: UUID) -> UUID:
        response = self._request(
            "GET", f"workflows({flow_id})?$select=workflowid,_ownerid_value"
        )
        owner_id = response.get("_ownerid_value")
        if not isinstance(owner_id, str):
            raise FlowOwnershipError("flow owner response is malformed")
        return UUID(owner_id)

    def _request(
        self,
        method: str,
        relative_url: str,
        body: dict[str, JsonValue] | None = None,
        *,
        expected_status: int = 200,
    ) -> dict[str, JsonValue]:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            f"{self._api_url}/{relative_url}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0",
            },
        )
        status, response_body = self._transport(request)
        if status != expected_status:
            raise FlowOwnershipError(f"Dataverse {method} failed with HTTP {status}")
        if not response_body:
            return {}
        decoded = cast(JsonValue, json.loads(response_body))
        if not isinstance(decoded, dict):
            raise FlowOwnershipError("Dataverse response must be a JSON object")
        return decoded


def _send(request: urllib.request.Request) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        error.read()
        return error.code, b""
    except urllib.error.URLError as error:
        raise FlowOwnershipError("Dataverse request failed") from error


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("value must be a GUID") from error


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("assign", "verify"))
    parser.add_argument("--environment-url", required=True)
    parser.add_argument("--flow-id", type=_uuid, required=True)
    parser.add_argument("--application-id", type=_uuid, required=True)
    parser.add_argument("--token-env", default="DATAVERSE_ACCESS_TOKEN")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    token = os.environ.get(args.token_env, "")
    client = DataverseClient(args.environment_url, token)
    application_user_id = client.application_user_id(args.application_id)
    if args.action == "assign":
        client.assign_flow(args.flow_id, application_user_id)
    actual_owner_id = client.flow_owner_id(args.flow_id)
    if actual_owner_id != application_user_id:
        raise FlowOwnershipError("flow owner does not match the application user")
    print(f"Flow owner verified: {args.flow_id}")


if __name__ == "__main__":
    try:
        main()
    except FlowOwnershipError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
