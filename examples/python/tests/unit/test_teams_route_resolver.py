"""Microsoft Teams logical route resolution tests."""

import pytest

from pyhookkit.adapters.outbound.teams.route_resolver import (
    TeamsEnvironmentRouteResolver,
    TeamsRouteNotConfiguredError,
)


def test_route_resolves_through_environment_variable() -> None:
    resolver = TeamsEnvironmentRouteResolver({"platform-alerts": "TEAMS_WORKFLOW_URL"})

    assert (
        resolver.resolve(
            "platform-alerts",
            {"TEAMS_WORKFLOW_URL": "https://workflow.example.com/hook"},
        )
        == "https://workflow.example.com/hook"
    )


@pytest.mark.parametrize(
    ("route", "environment"),
    [
        ("unknown", {"TEAMS_WORKFLOW_URL": "https://workflow.example.com/hook"}),
        ("platform-alerts", {}),
        ("platform-alerts", {"TEAMS_WORKFLOW_URL": " "}),
    ],
)
def test_route_rejects_missing_configuration(
    route: str,
    environment: dict[str, str],
) -> None:
    resolver = TeamsEnvironmentRouteResolver({"platform-alerts": "TEAMS_WORKFLOW_URL"})

    with pytest.raises(TeamsRouteNotConfiguredError):
        resolver.resolve(route, environment)
