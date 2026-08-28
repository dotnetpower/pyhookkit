"""Slack Web API client and cursor pagination tests."""

from collections.abc import Mapping
from typing import cast

import httpx
import pytest

from pyhookkit.adapters.outbound.slack.pagination import (
    SlackPaginationError,
    collect_slack_items,
    collect_slack_strings,
)
from pyhookkit.adapters.outbound.slack.web_api import (
    SlackAppToken,
    SlackBotToken,
    SlackWebApi,
    SlackWebApiClient,
    SlackWebApiError,
    SlackWebApiErrorKind,
)
from pyhookkit.json_types import JsonObject

_TOKEN_VALUE = "xoxb-000000000000-synthetic"


def _response(
    status_code: int,
    payload: object,
    *,
    headers: Mapping[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        headers=headers,
        request=httpx.Request("POST", "https://slack.com/api/test"),
    )


def test_bot_token_is_validated_and_redacted() -> None:
    token = SlackBotToken(_TOKEN_VALUE)

    assert token.value == _TOKEN_VALUE
    assert _TOKEN_VALUE not in repr(token)
    with pytest.raises(ValueError, match="invalid Slack bot token"):
        SlackBotToken("not-a-token")


def test_app_token_is_validated_and_redacted() -> None:
    token_value = "xapp-000000000000-synthetic"
    token = SlackAppToken(token_value)

    assert token.value == token_value
    assert token_value not in repr(token)
    with pytest.raises(ValueError, match="invalid Slack app token"):
        SlackAppToken("not-a-token")


def test_client_sends_bearer_json_and_returns_success() -> None:
    requests: list[tuple[str, dict[str, object]]] = []

    def post(url: str, **kwargs: object) -> httpx.Response:
        requests.append((url, kwargs))
        return _response(200, {"ok": True, "team_id": "T00000001"})

    result = SlackWebApiClient(SlackBotToken(_TOKEN_VALUE), post=post).call("auth.test")

    assert result["team_id"] == "T00000001"
    url, arguments = requests[0]
    assert url == "https://slack.com/api/auth.test"
    headers = cast(dict[str, str], arguments["headers"])
    assert headers["Authorization"] == f"Bearer {_TOKEN_VALUE}"
    assert arguments["json"] == {}
    scheme, token = headers["Authorization"].split(maxsplit=1)
    assert scheme == "Bearer"
    assert token == _TOKEN_VALUE


@pytest.mark.parametrize(
    ("payload", "expected_kind"),
    [
        ({"ok": False, "error": "invalid_auth"}, SlackWebApiErrorKind.AUTHENTICATION),
        ({"ok": False, "error": "missing_scope"}, SlackWebApiErrorKind.PERMISSION),
        ({"ok": False, "error": "channel_not_found"}, SlackWebApiErrorKind.NOT_FOUND),
        ({"unexpected": True}, SlackWebApiErrorKind.PERMANENT),
    ],
)
def test_client_classifies_json_failures(
    payload: object,
    expected_kind: SlackWebApiErrorKind,
) -> None:
    client = SlackWebApiClient(
        SlackBotToken(_TOKEN_VALUE),
        post=lambda *_args, **_kwargs: _response(200, payload),
    )

    with pytest.raises(SlackWebApiError) as captured:
        client.call("chat.postMessage", {"channel": "C00000001"})

    assert captured.value.kind is expected_kind
    assert _TOKEN_VALUE not in repr(captured.value)


def test_client_retries_rate_limit_without_exposing_response() -> None:
    responses = [
        _response(429, {"ok": False}, headers={"Retry-After": "2"}),
        _response(200, {"ok": True}),
    ]
    delays: list[float] = []
    client = SlackWebApiClient(
        SlackBotToken(_TOKEN_VALUE),
        post=lambda *_args, **_kwargs: responses.pop(0),
        sleep=delays.append,
        jitter=lambda: 0.5,
    )

    assert client.call("auth.test")["ok"] is True
    assert delays == [2.0]


def test_client_retries_json_rate_limit() -> None:
    responses = [
        _response(
            200,
            {"ok": False, "error": "ratelimited"},
            headers={"Retry-After": "1"},
        ),
        _response(200, {"ok": True}),
    ]
    delays: list[float] = []
    client = SlackWebApiClient(
        SlackBotToken(_TOKEN_VALUE),
        post=lambda *_args, **_kwargs: responses.pop(0),
        sleep=delays.append,
        jitter=lambda: 0.5,
    )

    assert client.call("auth.test")["ok"] is True
    assert delays == [1.0]


def test_client_retries_transient_http_failure_then_stops() -> None:
    client = SlackWebApiClient(
        SlackBotToken(_TOKEN_VALUE),
        post=lambda *_args, **_kwargs: _response(503, {"error": "sensitive"}),
        sleep=lambda _delay: None,
    )

    with pytest.raises(SlackWebApiError) as captured:
        client.call("auth.test")

    assert captured.value.kind is SlackWebApiErrorKind.TRANSIENT
    assert captured.value.status_code == 503


@pytest.mark.parametrize(
    ("status_code", "expected_kind"),
    [
        (401, SlackWebApiErrorKind.AUTHENTICATION),
        (403, SlackWebApiErrorKind.PERMISSION),
        (400, SlackWebApiErrorKind.INVALID_REQUEST),
    ],
)
def test_client_classifies_non_success_http_status(
    status_code: int,
    expected_kind: SlackWebApiErrorKind,
) -> None:
    client = SlackWebApiClient(
        SlackBotToken(_TOKEN_VALUE),
        post=lambda *_args, **_kwargs: _response(status_code, {}),
    )

    with pytest.raises(SlackWebApiError) as captured:
        client.call("auth.test")

    assert captured.value.kind is expected_kind


def test_client_rejects_malformed_method_and_response() -> None:
    client = SlackWebApiClient(
        SlackBotToken(_TOKEN_VALUE),
        post=lambda *_args, **_kwargs: _response(200, ["not", "an", "object"]),
    )

    with pytest.raises(ValueError, match="invalid Slack Web API method"):
        client.call("https://example.com")
    with pytest.raises(SlackWebApiError) as captured:
        client.call("auth.test")
    assert captured.value.kind is SlackWebApiErrorKind.MALFORMED_RESPONSE


class StubApi:
    def __init__(self, pages: list[JsonObject]) -> None:
        self._pages = pages
        self.parameters: list[Mapping[str, object] | None] = []

    def call(
        self,
        method: str,
        payload: Mapping[str, object] | None = None,
    ) -> JsonObject:
        assert method == "conversations.list"
        self.parameters.append(payload)
        return self._pages.pop(0)


def test_cursor_pagination_collects_all_items() -> None:
    api = StubApi(
        [
            {
                "ok": True,
                "channels": [{"id": "C1"}],
                "response_metadata": {"next_cursor": "next"},
            },
            {
                "ok": True,
                "channels": [{"id": "C2"}],
                "response_metadata": {"next_cursor": ""},
            },
        ]
    )

    result = collect_slack_items(
        cast(SlackWebApi, api),
        method="conversations.list",
        collection_key="channels",
        parameters={"limit": 200},
    )

    assert result == ({"id": "C1"}, {"id": "C2"})
    assert api.parameters[1] == {"limit": 200, "cursor": "next"}


def test_cursor_pagination_rejects_malformed_collection() -> None:
    api = StubApi([{"ok": True, "channels": "not-a-list"}])

    with pytest.raises(SlackPaginationError):
        collect_slack_items(
            cast(SlackWebApi, api),
            method="conversations.list",
            collection_key="channels",
        )


def test_string_cursor_pagination_collects_members() -> None:
    api = StubApi(
        [
            {
                "ok": True,
                "channels": ["U00000001", "U00000002"],
                "response_metadata": {"next_cursor": ""},
            }
        ]
    )

    assert collect_slack_strings(
        cast(SlackWebApi, api),
        method="conversations.list",
        collection_key="channels",
    ) == ("U00000001", "U00000002")
