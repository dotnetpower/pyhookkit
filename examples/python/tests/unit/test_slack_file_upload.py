"""Slack external file upload sequence tests."""

from collections.abc import Mapping
from typing import cast

import httpx
import pytest

from pyhookkit.adapters.outbound.slack.file_upload import (
    SlackFileUploader,
    SlackFileUploadError,
)
from pyhookkit.adapters.outbound.slack.web_api import SlackWebApi
from pyhookkit.json_types import JsonObject


class StubApi:
    def __init__(self, responses: list[JsonObject]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, Mapping[str, object] | None]] = []

    def call(
        self,
        method: str,
        payload: Mapping[str, object] | None = None,
    ) -> JsonObject:
        self.calls.append((method, payload))
        return self.responses.pop(0)


def test_upload_uses_current_three_step_sequence() -> None:
    api = StubApi(
        [
            {
                "ok": True,
                "upload_url": "https://files.slack.com/upload/v1/synthetic",
                "file_id": "F00000001",
            },
            {"ok": True},
        ]
    )
    uploads: list[tuple[str, dict[str, object]]] = []

    def upload(url: str, **kwargs: object) -> httpx.Response:
        uploads.append((url, kwargs))
        return httpx.Response(200)

    result = SlackFileUploader(
        cast(SlackWebApi, api),
        upload=upload,
    ).upload(
        filename="synthetic.txt",
        title="Synthetic report",
        content=b"safe content",
        channel_id="C00000001",
    )

    assert result.identifier == "F00000001"
    assert api.calls[0] == (
        "files.getUploadURLExternal",
        {"filename": "synthetic.txt", "length": 12},
    )
    assert api.calls[1][0] == "files.completeUploadExternal"
    assert uploads[0][1]["content"] == b"safe content"


def test_upload_rejects_provider_supplied_non_slack_url() -> None:
    api = StubApi(
        [
            {
                "ok": True,
                "upload_url": "https://malicious.example/upload",
                "file_id": "F00000001",
            }
        ]
    )

    with pytest.raises(SlackFileUploadError, match="invalid"):
        SlackFileUploader(cast(SlackWebApi, api)).upload(
            filename="synthetic.txt",
            title="Synthetic report",
            content=b"safe",
            channel_id="C00000001",
        )


def test_upload_rejects_non_success_binary_response() -> None:
    api = StubApi(
        [
            {
                "ok": True,
                "upload_url": "https://files.slack.com/upload/v1/synthetic",
                "file_id": "F00000001",
            }
        ]
    )

    with pytest.raises(SlackFileUploadError, match="data upload"):
        SlackFileUploader(
            cast(SlackWebApi, api),
            upload=lambda *_args, **_kwargs: httpx.Response(500),
        ).upload(
            filename="synthetic.txt",
            title="Synthetic report",
            content=b"safe",
            channel_id="C00000001",
        )


@pytest.mark.parametrize(
    ("filename", "title", "content"),
    [
        ("../secret.txt", "Report", b"safe"),
        ("safe.txt", " ", b"safe"),
        ("safe.txt", "Report", b""),
    ],
)
def test_upload_rejects_invalid_local_input(
    filename: str,
    title: str,
    content: bytes,
) -> None:
    with pytest.raises(ValueError):
        SlackFileUploader(cast(SlackWebApi, StubApi([]))).upload(
            filename=filename,
            title=title,
            content=content,
            channel_id="C00000001",
        )
