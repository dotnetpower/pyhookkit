"""Reusable scenario builder tests."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyhookkit.adapters.outbound.canonical_notification_json import (
    canonical_notification_to_json,
)
from pyhookkit.application.scenarios.approval_request import (
    ApprovalRequestEvent,
)
from pyhookkit.application.scenarios.approval_request import (
    build_example_notification as build_approval_request_example_notification,
)
from pyhookkit.application.scenarios.deployment_result import (
    DeploymentResultEvent,
)
from pyhookkit.application.scenarios.deployment_result import (
    build_example_notification as build_deployment_result_example_notification,
)
from pyhookkit.application.scenarios.incident_alert_acknowledgment import (
    IncidentAlertAcknowledgmentEvent,
)
from pyhookkit.application.scenarios.incident_alert_acknowledgment import (
    build_example_notification as build_incident_alert_example_notification,
)
from pyhookkit.application.scenarios.maintenance_notice import (
    MaintenanceNoticeEvent,
)
from pyhookkit.application.scenarios.maintenance_notice import (
    build_example_notification as build_maintenance_notice_example_notification,
)
from pyhookkit.application.scenarios.maintenance_notice import (
    build_notification as build_maintenance_notice_notification,
)
from pyhookkit.domain.notification import CanonicalNotification

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_SCENARIO_VECTORS = _REPOSITORY_ROOT / "contracts" / "test-vectors" / "scenarios"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("vector_name", "builder"),
    [
        ("deployment-result", build_deployment_result_example_notification),
        (
            "incident-alert-acknowledgment",
            build_incident_alert_example_notification,
        ),
        ("approval-request", build_approval_request_example_notification),
        ("maintenance-notice", build_maintenance_notice_example_notification),
    ],
)
def test_example_builders_preserve_committed_canonical_notifications(
    vector_name: str,
    builder: Callable[[], CanonicalNotification],
) -> None:
    notification = builder()

    assert canonical_notification_to_json(notification) == _load_json(
        _SCENARIO_VECTORS / vector_name / "notification.json"
    )


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: DeploymentResultEvent(
                event_id="scenario-deployment-result-001",
                service=" ",
                deployment_environment="staging",
                revision="9f3a2c1",
                duration="2m 18s",
                completed_at=datetime(2026, 8, 28, 3, 15, tzinfo=UTC),
                deployment_url="https://deployments.example.com/runs/run-1042",
                correlation_id="deploy-run-1042",
            ),
            "service is invalid",
        ),
        (
            lambda: IncidentAlertAcknowledgmentEvent(
                event_id="scenario-incident-alert-001",
                incident_id="INC-204",
                service="example-checkout",
                started_at=datetime(2026, 8, 28, 4, 20, tzinfo=UTC),
                status="unacknowledged",
                responder_alias="Example Responders",
                acknowledgment_url=(
                    "https://incidents.example.com/incidents/inc-204/acknowledge"
                ),
                runbook_url=(
                    "https://runbooks.example.com/services/example-checkout/latency"
                ),
                correlation_id="incident-inc-204",
            ),
            "responder alias is invalid",
        ),
        (
            lambda: ApprovalRequestEvent(
                event_id="scenario-approval-request-001",
                request_id="APR-307",
                subject="example-api 2026.08.28",
                requester="example-requester",
                requested_at=datetime(2026, 8, 28, 5, 10),
                deadline_at=datetime(2026, 8, 28, 7, tzinfo=UTC),
                approver_alias="example-approver",
                review_url="https://approvals.example.com/requests/apr-307",
                correlation_id="approval-apr-307",
            ),
            "source timestamp must include a UTC offset",
        ),
        (
            lambda: MaintenanceNoticeEvent(
                event_id="scenario-maintenance-notice-001",
                window_start=datetime(2026, 8, 30, 1, tzinfo=UTC),
                window_end=datetime(2026, 8, 30, 2, tzinfo=UTC),
                announced_at=datetime(2026, 8, 28, 6, tzinfo=UTC),
                affected_services=(),
                expected_impact="Brief request retries",
                owner_alias="example-operations",
                status_page_url=("https://status.example.com/notices/maintenance-118"),
                correlation_id="maintenance-118",
            ),
            "affected services must contain at least one service",
        ),
    ],
)
def test_scenario_inputs_reject_invalid_values(
    factory: Callable[[], object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


def test_maintenance_notice_supports_dynamic_service_lists() -> None:
    notification = build_maintenance_notice_notification(
        MaintenanceNoticeEvent(
            event_id="scenario-maintenance-notice-002",
            window_start=datetime(2026, 8, 30, 1, tzinfo=UTC),
            window_end=datetime(2026, 8, 30, 2, tzinfo=UTC),
            announced_at=datetime(2026, 8, 28, 6, tzinfo=UTC),
            affected_services=("example-api", "example-worker", "example-billing"),
            expected_impact="Brief request retries",
            owner_alias="example-operations",
            status_page_url="https://status.example.com/notices/maintenance-119",
            correlation_id="maintenance-119",
        )
    )

    assert "example-api, example-worker, and example-billing" in notification.body
    assert notification.facts[1].value == "example-api, example-worker, example-billing"
