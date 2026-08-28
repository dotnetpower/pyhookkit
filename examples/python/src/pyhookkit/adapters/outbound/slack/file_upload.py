"""Slack external file upload sequence."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import PurePath
from urllib.parse import urlsplit

import httpx

from pyhookkit.adapters.outbound.slack.web_api import SlackWebApi


class SlackFileUploadError(RuntimeError):
    """A redacted Slack file upload failure."""


@dataclass(frozen=True, slots=True)
class SlackFileReference:
    identifier: str
    title: str


class SlackFileUploader:
    """Run Slack's get URL, upload bytes, and complete sequence."""

    def __init__(
        self,
        api: SlackWebApi,
        *,
        upload: Callable[..., httpx.Response] = httpx.post,
        timeout_seconds: float = 30.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Slack file upload timeout must be positive")
        self._api = api
        self._upload = upload
        self._timeout_seconds = timeout_seconds

    def upload(
        self,
        *,
        filename: str,
        title: str,
        content: bytes,
        channel_id: str,
        initial_comment: str | None = None,
    ) -> SlackFileReference:
        _validate_file(filename, title, content)
        ticket = self._api.call(
            "files.getUploadURLExternal",
            {"filename": filename, "length": len(content)},
        )
        upload_url = _required_string(
            ticket,
            "upload_url",
            "files.getUploadURLExternal",
        )
        _validate_upload_url(upload_url)
        file_id = _required_string(
            ticket,
            "file_id",
            "files.getUploadURLExternal",
        )
        try:
            response = self._upload(
                upload_url,
                content=content,
                headers={"Content-Type": "application/octet-stream"},
                timeout=self._timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.TransportError):
            raise SlackFileUploadError("Slack file data upload failed") from None
        if response.status_code != 200:
            raise SlackFileUploadError("Slack file data upload failed")
        completion: dict[str, object] = {
            "files": [{"id": file_id, "title": title}],
            "channel_id": channel_id,
        }
        if initial_comment is not None:
            completion["initial_comment"] = initial_comment
        self._api.call("files.completeUploadExternal", completion)
        return SlackFileReference(file_id, title)


def _validate_file(filename: str, title: str, content: bytes) -> None:
    if not filename or PurePath(filename).name != filename:
        raise ValueError("Slack upload filename must be a basename")
    if not title.strip():
        raise ValueError("Slack upload title must not be blank")
    if not content:
        raise ValueError("Slack upload content must not be empty")


def _validate_upload_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname != "files.slack.com":
        raise SlackFileUploadError("Slack returned an invalid file upload URL")


def _required_string(
    response: Mapping[str, object],
    key: str,
    method: str,
) -> str:
    value = response.get(key)
    if not isinstance(value, str) or not value:
        raise SlackFileUploadError(f"Slack {method} response requires {key}")
    return value
