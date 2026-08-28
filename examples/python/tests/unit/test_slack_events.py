"""Slack Events API HTTP handling tests."""

import hashlib
import hmac
import json

import pytest

from pyhookkit.adapters.inbound.slack.events import (
    SlackEventPayloadError,
    SlackEventsHttpHandler,
)
from pyhookkit.adapters.inbound.slack.request_signing import (
    SlackRequestVerificationError,
    SlackRequestVerifier,
    SlackSigningSecret,
)

_SECRET = "synthetic-signing-secret"
_TIMESTAMP = "1724811000"


def _headers(body: bytes) -> dict[str, str]:
    base = b"v0:" + _TIMESTAMP.encode() + b":" + body
    digest = hmac.new(_SECRET.encode(), base, hashlib.sha256).hexdigest()
    return {
        "X-Slack-Request-Timestamp": _TIMESTAMP,
        "X-Slack-Signature": f"v0={digest}",
    }


def _handler() -> SlackEventsHttpHandler:
    return SlackEventsHttpHandler(
        SlackRequestVerifier(
            SlackSigningSecret(_SECRET),
            clock=lambda: float(_TIMESTAMP),
        )
    )


def test_url_verification_returns_challenge() -> None:
    body = json.dumps(
        {"type": "url_verification", "challenge": "synthetic-challenge"}
    ).encode()

    acknowledgment = _handler().handle(_headers(body), body)

    assert acknowledgment.body == b"synthetic-challenge"
    assert acknowledgment.event is None


def test_app_mention_is_acknowledged_without_echoing_payload() -> None:
    body = json.dumps(
        {
            "type": "event_callback",
            "event_id": "Ev00000001",
            "team_id": "T00000001",
            "event": {
                "type": "app_mention",
                "user": "U00000001",
                "channel": "C00000001",
                "text": "sensitive synthetic body",
            },
        }
    ).encode()

    acknowledgment = _handler().handle(_headers(body), body)

    assert acknowledgment.body == b""
    assert acknowledgment.event is not None
    assert acknowledgment.event.event_type == "app_mention"
    assert "sensitive synthetic body" not in repr(acknowledgment)


@pytest.mark.parametrize(
    ("event_type", "subtype"),
    [
        ("reaction_added", None),
        ("message", "message_deleted"),
        ("tokens_revoked", None),
        ("app_uninstalled", None),
    ],
)
def test_lifecycle_events_are_acknowledged(
    event_type: str,
    subtype: str | None,
) -> None:
    event: dict[str, object] = {"type": event_type}
    if subtype is not None:
        event["subtype"] = subtype
    body = json.dumps(
        {
            "type": "event_callback",
            "event_id": "Ev00000001",
            "team_id": "T00000001",
            "event": event,
        }
    ).encode()

    acknowledgment = _handler().handle(_headers(body), body)

    assert acknowledgment.event is not None
    assert acknowledgment.event.event_type == event_type
    assert acknowledgment.event.subtype == subtype


def test_bad_signature_is_rejected_before_payload_parsing() -> None:
    body = b"not-json"

    with pytest.raises(SlackRequestVerificationError):
        _handler().handle(
            {
                "X-Slack-Request-Timestamp": _TIMESTAMP,
                "X-Slack-Signature": "v0=invalid",
            },
            body,
        )


def test_unsupported_event_envelope_is_rejected() -> None:
    body = json.dumps({"type": "unknown"}).encode()

    with pytest.raises(SlackEventPayloadError, match="unsupported"):
        _handler().handle(_headers(body), body)


def test_unsupported_event_type_is_rejected() -> None:
    body = json.dumps(
        {
            "type": "event_callback",
            "event_id": "Ev00000001",
            "team_id": "T00000001",
            "event": {"type": "unsupported"},
        }
    ).encode()

    with pytest.raises(SlackEventPayloadError, match="event type"):
        _handler().handle(_headers(body), body)
