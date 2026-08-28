"""Slack interactive approval rendering and verification tests."""

import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from pyhookkit.adapters.inbound.slack.approval_interaction import (
    ApprovalDecision,
    SlackInteractionPayloadError,
    parse_slack_approval,
)
from pyhookkit.adapters.inbound.slack.request_signing import (
    SlackRequestVerificationError,
    SlackRequestVerifier,
    SlackSigningSecret,
)
from pyhookkit.adapters.outbound.slack.approval_renderer import (
    SlackApprovalRenderer,
)
from pyhookkit.domain.notification import CanonicalNotification, Severity

_SECRET_VALUE = "synthetic-signing-secret"
_TIMESTAMP = "1724811000"


def _notification() -> CanonicalNotification:
    return CanonicalNotification(
        schema_version="1.0",
        event_id="example-approval-001",
        route="release-approvals",
        body="Approve the synthetic release.",
        severity=Severity.WARNING,
    )


def _body(action_id: str = "approval_approve") -> bytes:
    payload = {
        "type": "block_actions",
        "user": {"id": "U00000001"},
        "channel": {"id": "C00000001"},
        "message": {"ts": "1724811000.000001"},
        "actions": [{"action_id": action_id, "value": "example-approval-001"}],
    }
    return urlencode({"payload": json.dumps(payload)}).encode()


def _signature(body: bytes) -> str:
    base = b"v0:" + _TIMESTAMP.encode() + b":" + body
    digest = hmac.new(_SECRET_VALUE.encode(), base, hashlib.sha256).hexdigest()
    return f"v0={digest}"


def test_approval_renderer_adds_two_explicit_actions() -> None:
    payload = SlackApprovalRenderer().render(_notification())

    assert "approval_approve" in json.dumps(payload)
    assert "approval_reject" in json.dumps(payload)


def test_signed_approval_is_verified_and_parsed() -> None:
    body = _body()
    verifier = SlackRequestVerifier(
        SlackSigningSecret(_SECRET_VALUE),
        clock=lambda: float(_TIMESTAMP),
    )

    verifier.verify(_TIMESTAMP, _signature(body), body)
    interaction = parse_slack_approval(body)

    assert interaction.decision is ApprovalDecision.APPROVED
    assert interaction.event_id == "example-approval-001"


def test_verifier_rejects_bad_signature_and_stale_request() -> None:
    body = _body()
    current = float(_TIMESTAMP)
    verifier = SlackRequestVerifier(
        SlackSigningSecret(_SECRET_VALUE),
        clock=lambda: current,
    )

    with pytest.raises(SlackRequestVerificationError, match="signature"):
        verifier.verify(_TIMESTAMP, "v0=invalid", body)
    stale = SlackRequestVerifier(
        SlackSigningSecret(_SECRET_VALUE),
        clock=lambda: current + 301,
    )
    with pytest.raises(SlackRequestVerificationError, match="stale"):
        stale.verify(_TIMESTAMP, _signature(body), body)


def test_parser_rejects_unrelated_action() -> None:
    with pytest.raises(SlackInteractionPayloadError, match="unsupported"):
        parse_slack_approval(_body("unrelated_action"))


def test_signing_secret_is_redacted() -> None:
    secret = SlackSigningSecret(_SECRET_VALUE)

    assert _SECRET_VALUE not in repr(secret)
