"""Automation CLI for dynamic paired scenario notifications."""

import argparse
import os
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from pyhookkit.adapters.inbound.canonical_notification_json import (
    load_canonical_notification,
)
from pyhookkit.adapters.outbound.slack.identity import (
    SlackIdentity,
    SlackIdentityDirectory,
)
from pyhookkit.adapters.outbound.slack.message_renderer import SlackMessageRenderer
from pyhookkit.adapters.outbound.teams.identity import (
    TeamsIdentity,
    TeamsIdentityDirectory,
)
from pyhookkit.adapters.outbound.teams.message_renderer import (
    TeamsGroupMentionPolicy,
    TeamsMessageRenderer,
)
from pyhookkit.application.scenarios.approval_request import (
    ApprovalRequestEvent,
)
from pyhookkit.application.scenarios.approval_request import (
    build_notification as build_approval_request_notification,
)
from pyhookkit.application.scenarios.deployment_result import (
    DeploymentResultEvent,
)
from pyhookkit.application.scenarios.deployment_result import (
    build_notification as build_deployment_result_notification,
)
from pyhookkit.application.scenarios.incident_alert_acknowledgment import (
    IncidentAlertAcknowledgmentEvent,
)
from pyhookkit.application.scenarios.incident_alert_acknowledgment import (
    build_notification as build_incident_alert_acknowledgment_notification,
)
from pyhookkit.application.scenarios.maintenance_notice import (
    MaintenanceNoticeEvent,
)
from pyhookkit.application.scenarios.maintenance_notice import (
    build_notification as build_maintenance_notice_notification,
)
from pyhookkit.domain.notification import (
    CanonicalNotification,
    Mention,
    MentionKind,
)
from pyhookkit.entrypoints.slack_webhook_example import run_slack_webhook_example
from pyhookkit.entrypoints.teams_workflow_example import run_teams_workflow_example
from pyhookkit.ports.message_renderer import MessageRenderer

_SCENARIOS = (
    "deployment-result",
    "incident-alert-acknowledgment",
    "approval-request",
    "maintenance-notice",
)
_PROVIDERS = ("slack", "teams")


def run_notification_automation(
    *,
    arguments: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Render or send one scenario notification or canonical input file."""
    parser = _build_parser()
    parsed = parser.parse_args(arguments)
    scenario, provider = _resolve_mode(parser, parsed)
    notification, renderer = _notification_and_renderer(
        parser,
        parsed,
        scenario,
        provider,
    )
    active_environment = os.environ if environment is None else environment
    runner_arguments: list[str] = ["--send"] if parsed.send else []
    if provider == "slack":
        run_slack_webhook_example(
            notification,
            renderer,
            arguments=runner_arguments,
            environment=active_environment,
        )
        return
    run_teams_workflow_example(
        notification,
        renderer,
        arguments=runner_arguments,
        environment=active_environment,
    )


def main() -> None:
    """Run the automation CLI with CLI-friendly error handling."""
    try:
        run_notification_automation()
    except ValueError as error:
        raise SystemExit(str(error)) from error


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render or send one reusable PyHookKit scenario notification.",
    )
    parser.add_argument("scenario", nargs="?", choices=_SCENARIOS)
    parser.add_argument("provider", nargs="?", choices=_PROVIDERS)
    parser.add_argument("--provider", choices=_PROVIDERS, dest="provider_option")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--event-id")
    parser.add_argument("--correlation-id")
    parser.add_argument("--route")
    parser.add_argument("--source")
    parser.add_argument("--hero-image-url")
    parser.add_argument("--teams-compact", action="store_true")
    parser.add_argument(
        "--teams-hide-group-mention-notice",
        action="store_true",
    )

    deployment = parser.add_argument_group("deployment result")
    deployment.add_argument("--service")
    deployment.add_argument("--deployment-environment")
    deployment.add_argument("--revision")
    deployment.add_argument("--duration")
    deployment.add_argument("--completed-at", type=_parse_timestamp)
    deployment.add_argument("--deployment-url")

    incident = parser.add_argument_group("incident alert acknowledgment")
    incident.add_argument("--incident-id")
    incident.add_argument("--incident-service")
    incident.add_argument("--started-at", type=_parse_timestamp)
    incident.add_argument("--status")
    incident.add_argument("--responder-alias")
    incident.add_argument("--acknowledgment-url")
    incident.add_argument("--runbook-url")
    incident.add_argument("--thread-key")

    approval = parser.add_argument_group("approval request")
    approval.add_argument("--request-id")
    approval.add_argument("--subject")
    approval.add_argument("--requester")
    approval.add_argument("--requested-at", type=_parse_timestamp)
    approval.add_argument("--deadline-at", type=_parse_timestamp)
    approval.add_argument("--approver-alias")
    approval.add_argument("--review-url")

    maintenance = parser.add_argument_group("maintenance notice")
    maintenance.add_argument("--window-start", type=_parse_timestamp)
    maintenance.add_argument("--window-end", type=_parse_timestamp)
    maintenance.add_argument("--announced-at", type=_parse_timestamp)
    maintenance.add_argument("--affected-service", action="append")
    maintenance.add_argument("--expected-impact")
    maintenance.add_argument("--owner-alias")
    maintenance.add_argument("--status-page-url")

    provider_group = parser.add_argument_group("provider identity configuration")
    provider_group.add_argument("--slack-approver-id")
    provider_group.add_argument("--slack-responder-group-id")
    provider_group.add_argument("--slack-owner-group-id")
    provider_group.add_argument("--teams-approver-id")
    provider_group.add_argument("--teams-approver-name")
    provider_group.add_argument("--slack-user-identity", action="append")
    provider_group.add_argument("--slack-group-identity", action="append")
    provider_group.add_argument("--teams-user-identity", action="append")
    provider_group.add_argument("--teams-user-display-name", action="append")
    return parser


def _resolve_mode(
    parser: argparse.ArgumentParser,
    parsed: argparse.Namespace,
) -> tuple[str | None, str]:
    provider = parsed.provider_option or parsed.provider
    if provider is None:
        parser.error("provider is required")
    if (
        parsed.provider_option is not None
        and parsed.provider is not None
        and parsed.provider_option != parsed.provider
    ):
        parser.error("--provider must match the positional provider when both are set")
    if parsed.input is None and parsed.scenario is None:
        parser.error("scenario is required unless --input is provided")
    return parsed.scenario, provider


def _notification_and_renderer(
    parser: argparse.ArgumentParser,
    parsed: argparse.Namespace,
    scenario: str | None,
    provider: str,
) -> tuple[CanonicalNotification, MessageRenderer]:
    if parsed.input is not None:
        notification = load_canonical_notification(parsed.input)
        return notification, _input_renderer(parsed, provider, notification, scenario)

    event_id = _required_argument(parser, parsed.event_id, "--event-id")
    correlation_id = _required_argument(
        parser,
        parsed.correlation_id,
        "--correlation-id",
    )
    if scenario == "deployment-result":
        event = DeploymentResultEvent(
            event_id=event_id,
            service=_required_argument(parser, parsed.service, "--service"),
            deployment_environment=_required_argument(
                parser,
                parsed.deployment_environment,
                "--deployment-environment",
            ),
            revision=_required_argument(parser, parsed.revision, "--revision"),
            duration=_required_argument(parser, parsed.duration, "--duration"),
            completed_at=_required_argument(
                parser,
                parsed.completed_at,
                "--completed-at",
            ),
            deployment_url=_required_argument(
                parser,
                parsed.deployment_url,
                "--deployment-url",
            ),
            correlation_id=correlation_id,
            route=parsed.route or "release-notifications",
            source=parsed.source or "synthetic-release-service",
        )
        return (
            build_deployment_result_notification(event),
            _deployment_renderer(provider, parsed),
        )

    if scenario == "incident-alert-acknowledgment":
        event = IncidentAlertAcknowledgmentEvent(
            event_id=event_id,
            incident_id=_required_argument(
                parser,
                parsed.incident_id,
                "--incident-id",
            ),
            service=_required_argument(
                parser,
                parsed.incident_service,
                "--incident-service",
            ),
            started_at=_required_argument(parser, parsed.started_at, "--started-at"),
            status=_required_argument(parser, parsed.status, "--status"),
            responder_alias=_required_argument(
                parser,
                parsed.responder_alias,
                "--responder-alias",
            ),
            acknowledgment_url=_required_argument(
                parser,
                parsed.acknowledgment_url,
                "--acknowledgment-url",
            ),
            runbook_url=_required_argument(
                parser,
                parsed.runbook_url,
                "--runbook-url",
            ),
            correlation_id=correlation_id,
            route=parsed.route or "incident-response",
            source=parsed.source or "synthetic-incident-service",
            thread_key=parsed.thread_key,
        )
        return (
            build_incident_alert_acknowledgment_notification(event),
            _incident_renderer(
                parser,
                provider,
                parsed,
                event.responder_alias,
            ),
        )

    if scenario == "approval-request":
        event = ApprovalRequestEvent(
            event_id=event_id,
            request_id=_required_argument(parser, parsed.request_id, "--request-id"),
            subject=_required_argument(parser, parsed.subject, "--subject"),
            requester=_required_argument(parser, parsed.requester, "--requester"),
            requested_at=_required_argument(
                parser,
                parsed.requested_at,
                "--requested-at",
            ),
            deadline_at=_required_argument(
                parser,
                parsed.deadline_at,
                "--deadline-at",
            ),
            approver_alias=_required_argument(
                parser,
                parsed.approver_alias,
                "--approver-alias",
            ),
            review_url=_required_argument(parser, parsed.review_url, "--review-url"),
            correlation_id=correlation_id,
            route=parsed.route or "change-approvals",
            source=parsed.source or "synthetic-change-service",
        )
        return (
            build_approval_request_notification(event),
            _approval_renderer(
                parser,
                provider,
                parsed,
                event.approver_alias,
            ),
        )

    event = MaintenanceNoticeEvent(
        event_id=event_id,
        window_start=_required_argument(parser, parsed.window_start, "--window-start"),
        window_end=_required_argument(parser, parsed.window_end, "--window-end"),
        announced_at=_required_argument(
            parser,
            parsed.announced_at,
            "--announced-at",
        ),
        affected_services=_required_services(parser, parsed.affected_service),
        expected_impact=_required_argument(
            parser,
            parsed.expected_impact,
            "--expected-impact",
        ),
        owner_alias=_required_argument(parser, parsed.owner_alias, "--owner-alias"),
        status_page_url=_required_argument(
            parser,
            parsed.status_page_url,
            "--status-page-url",
        ),
        correlation_id=correlation_id,
        route=parsed.route or "service-announcements",
        source=parsed.source or "synthetic-maintenance-service",
    )
    return (
        build_maintenance_notice_notification(event),
        _maintenance_renderer(
            parser,
            provider,
            parsed,
            event.owner_alias,
        ),
    )


def _deployment_renderer(
    provider: str,
    parsed: argparse.Namespace,
) -> MessageRenderer:
    if provider == "slack":
        return _slack_renderer(None, parsed.hero_image_url)
    return _teams_renderer(None, parsed)


def _incident_renderer(
    parser: argparse.ArgumentParser,
    provider: str,
    parsed: argparse.Namespace,
    responder_alias: str,
) -> MessageRenderer:
    if provider == "slack":
        slack_group_id = _required_argument(
            parser,
            parsed.slack_responder_group_id,
            "--slack-responder-group-id",
        )
        return _slack_renderer(
            SlackIdentityDirectory(
                {
                    responder_alias: SlackIdentity(
                        MentionKind.GROUP,
                        slack_group_id,
                    )
                }
            ),
            parsed.hero_image_url,
        )
    return _teams_renderer(None, parsed)


def _approval_renderer(
    parser: argparse.ArgumentParser,
    provider: str,
    parsed: argparse.Namespace,
    approver_alias: str,
) -> MessageRenderer:
    if provider == "slack":
        slack_user_id = _required_argument(
            parser,
            parsed.slack_approver_id,
            "--slack-approver-id",
        )
        return _slack_renderer(
            SlackIdentityDirectory(
                {
                    approver_alias: SlackIdentity(
                        MentionKind.USER,
                        slack_user_id,
                    )
                }
            ),
            parsed.hero_image_url,
        )
    teams_user_id = _required_argument(
        parser,
        parsed.teams_approver_id,
        "--teams-approver-id",
    )
    teams_user_name = _required_argument(
        parser,
        parsed.teams_approver_name,
        "--teams-approver-name",
    )
    return _teams_renderer(
        TeamsIdentityDirectory(
            {
                approver_alias: TeamsIdentity(
                    teams_user_id,
                    teams_user_name,
                )
            }
        ),
        parsed,
    )


def _maintenance_renderer(
    parser: argparse.ArgumentParser,
    provider: str,
    parsed: argparse.Namespace,
    owner_alias: str,
) -> MessageRenderer:
    if provider == "slack":
        slack_group_id = _required_argument(
            parser,
            parsed.slack_owner_group_id,
            "--slack-owner-group-id",
        )
        return _slack_renderer(
            SlackIdentityDirectory(
                {
                    owner_alias: SlackIdentity(
                        MentionKind.GROUP,
                        slack_group_id,
                    )
                }
            ),
            parsed.hero_image_url,
        )
    return _teams_renderer(None, parsed)


def _input_renderer(
    parsed: argparse.Namespace,
    provider: str,
    notification: CanonicalNotification,
    scenario: str | None,
) -> MessageRenderer:
    if provider == "slack":
        user_mappings = _parse_alias_mappings(
            parsed.slack_user_identity,
            flag_name="--slack-user-identity",
        )
        group_mappings = _parse_alias_mappings(
            parsed.slack_group_identity,
            flag_name="--slack-group-identity",
        )
        _validate_slack_identities(notification.mentions, user_mappings, group_mappings)
        return SlackMessageRenderer(
            _slack_identity_directory(user_mappings, group_mappings)
        )

    team_identifiers = _parse_alias_mappings(
        parsed.teams_user_identity,
        flag_name="--teams-user-identity",
    )
    team_display_names = _parse_alias_mappings(
        parsed.teams_user_display_name,
        flag_name="--teams-user-display-name",
    )
    _validate_teams_identity_inputs(team_identifiers, team_display_names)
    _validate_teams_identities(notification.mentions, team_identifiers)
    teams_directory = _teams_identity_directory(team_identifiers, team_display_names)
    del scenario
    return _teams_renderer(teams_directory, parsed)


def _slack_identity_directory(
    user_mappings: Mapping[str, str],
    group_mappings: Mapping[str, str],
) -> SlackIdentityDirectory | None:
    identities: dict[str, SlackIdentity] = {}
    for alias, identifier in user_mappings.items():
        identities[alias] = SlackIdentity(MentionKind.USER, identifier)
    for alias, identifier in group_mappings.items():
        if alias in identities:
            raise ValueError(
                f"Slack identity alias is duplicated across input flags: {alias}"
            )
        identities[alias] = SlackIdentity(MentionKind.GROUP, identifier)
    if not identities:
        return None
    return SlackIdentityDirectory(identities)


def _slack_renderer(
    identity_directory: SlackIdentityDirectory | None,
    hero_image_url: str | None,
) -> SlackMessageRenderer:
    return SlackMessageRenderer(
        identity_directory,
        hero_image_url=hero_image_url,
    )


def _teams_identity_directory(
    identifiers: Mapping[str, str],
    display_names: Mapping[str, str],
) -> TeamsIdentityDirectory | None:
    if not identifiers:
        return None
    return TeamsIdentityDirectory(
        {
            alias: TeamsIdentity(identifier, display_names[alias])
            for alias, identifier in identifiers.items()
        }
    )


def _teams_renderer(
    identity_directory: TeamsIdentityDirectory | None,
    parsed: argparse.Namespace,
) -> TeamsMessageRenderer:
    return TeamsMessageRenderer(
        identity_directory,
        hero_image_url=parsed.hero_image_url,
        group_mention_policy=(
            TeamsGroupMentionPolicy.OMIT
            if parsed.teams_hide_group_mention_notice
            else TeamsGroupMentionPolicy.CONFIGURATION_NOTICE
        ),
        show_body_in_card=not parsed.teams_compact,
    )


def _validate_slack_identities(
    mentions: Sequence[Mention],
    user_mappings: Mapping[str, str],
    group_mappings: Mapping[str, str],
) -> None:
    missing_users = sorted(
        mention.alias
        for mention in mentions
        if mention.kind is MentionKind.USER and mention.alias not in user_mappings
    )
    if missing_users:
        aliases = ", ".join(missing_users)
        raise ValueError(
            "--slack-user-identity alias=USER_ID is required for canonical "
            f"input aliases: {aliases}"
        )
    missing_groups = sorted(
        mention.alias
        for mention in mentions
        if mention.kind is MentionKind.GROUP and mention.alias not in group_mappings
    )
    if missing_groups:
        aliases = ", ".join(missing_groups)
        raise ValueError(
            "--slack-group-identity alias=GROUP_ID is required for canonical "
            f"input aliases: {aliases}"
        )


def _validate_teams_identity_inputs(
    identifiers: Mapping[str, str],
    display_names: Mapping[str, str],
) -> None:
    missing_identifiers = sorted(display_names.keys() - identifiers.keys())
    if missing_identifiers:
        missing = ", ".join(missing_identifiers)
        raise ValueError(
            "--teams-user-identity is required for aliases declared in "
            f"--teams-user-display-name: {missing}"
        )
    missing_display_names = sorted(identifiers.keys() - display_names.keys())
    if missing_display_names:
        missing = ", ".join(missing_display_names)
        raise ValueError(
            "--teams-user-display-name is required for aliases declared in "
            f"--teams-user-identity: {missing}"
        )


def _validate_teams_identities(
    mentions: Sequence[Mention],
    team_identifiers: Mapping[str, str],
) -> None:
    missing_users = sorted(
        mention.alias
        for mention in mentions
        if mention.kind is MentionKind.USER and mention.alias not in team_identifiers
    )
    if missing_users:
        aliases = ", ".join(missing_users)
        raise ValueError(
            "Teams user mentions in canonical input require both "
            "--teams-user-identity alias=IDENTIFIER and "
            f"--teams-user-display-name alias=DISPLAY_NAME for aliases: {aliases}"
        )


def _parse_alias_mappings(
    raw_values: Sequence[str] | None,
    *,
    flag_name: str,
) -> dict[str, str]:
    mappings: dict[str, str] = {}
    for raw_value in raw_values or ():
        alias, separator, mapped_value = raw_value.partition("=")
        if not separator or not alias or not mapped_value:
            raise ValueError(f"{flag_name} must use alias=value")
        try:
            Mention(MentionKind.USER, alias)
        except ValueError as error:
            raise ValueError(f"{flag_name} alias is invalid: {alias}") from error
        if alias in mappings:
            raise ValueError(f"{flag_name} alias is duplicated: {alias}")
        mappings[alias] = mapped_value
    return mappings


def _required_argument[T](
    parser: argparse.ArgumentParser,
    value: T | None,
    flag_name: str,
) -> T:
    if value is None:
        parser.error(f"{flag_name} is required for the selected scenario/provider")
    return value


def _required_services(
    parser: argparse.ArgumentParser,
    services: Sequence[str] | None,
) -> tuple[str, ...]:
    if not services:
        parser.error("--affected-service is required for maintenance-notice")
    return tuple(services)


def _parse_timestamp(raw_value: str) -> datetime:
    normalized = raw_value.replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "timestamp must be ISO 8601 with a UTC offset"
        ) from error
    if timestamp.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must be ISO 8601 with a UTC offset")
    return timestamp


if __name__ == "__main__":
    main()
