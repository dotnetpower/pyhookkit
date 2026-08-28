"""Cursor pagination for Slack Web API collection methods."""

from collections.abc import Mapping
from typing import cast

from pyhookkit.adapters.outbound.slack.web_api import SlackWebApi
from pyhookkit.json_types import JsonObject


class SlackPaginationError(ValueError):
    """A Slack collection response has an invalid shape."""


def collect_slack_items(
    api: SlackWebApi,
    *,
    method: str,
    collection_key: str,
    parameters: Mapping[str, object] | None = None,
) -> tuple[JsonObject, ...]:
    """Collect every cursor page without silently discarding malformed items."""
    base_parameters = {} if parameters is None else dict(parameters)
    cursor: str | None = None
    items: list[JsonObject] = []
    while True:
        page_parameters = dict(base_parameters)
        if cursor is not None:
            page_parameters["cursor"] = cursor
        response = api.call(method, page_parameters)
        collection = response.get(collection_key)
        if not isinstance(collection, list):
            raise SlackPaginationError(
                f"Slack {method} response must contain {collection_key}"
            )
        for item in collection:
            if not isinstance(item, dict):
                raise SlackPaginationError(
                    f"Slack {method} returned a malformed collection item"
                )
            items.append(cast(JsonObject, item))
        cursor = _next_cursor(response, method)
        if cursor is None:
            return tuple(items)


def collect_slack_strings(
    api: SlackWebApi,
    *,
    method: str,
    collection_key: str,
    parameters: Mapping[str, object] | None = None,
) -> tuple[str, ...]:
    """Collect a cursor-paginated Slack string collection."""
    base_parameters = {} if parameters is None else dict(parameters)
    cursor: str | None = None
    items: list[str] = []
    while True:
        page_parameters = dict(base_parameters)
        if cursor is not None:
            page_parameters["cursor"] = cursor
        response = api.call(method, page_parameters)
        collection = response.get(collection_key)
        if not isinstance(collection, list):
            raise SlackPaginationError(
                f"Slack {method} response must contain string {collection_key}"
            )
        for item in collection:
            if not isinstance(item, str):
                raise SlackPaginationError(
                    f"Slack {method} response must contain string {collection_key}"
                )
            items.append(item)
        cursor = _next_cursor(response, method)
        if cursor is None:
            return tuple(items)


def _next_cursor(response: JsonObject, method: str) -> str | None:
    metadata = response.get("response_metadata")
    if metadata is None:
        return None
    if not isinstance(metadata, dict):
        raise SlackPaginationError(
            f"Slack {method} response_metadata must be an object"
        )
    next_cursor = metadata.get("next_cursor")
    if next_cursor in (None, ""):
        return None
    if not isinstance(next_cursor, str):
        raise SlackPaginationError(f"Slack {method} next_cursor must be a string")
    return next_cursor
