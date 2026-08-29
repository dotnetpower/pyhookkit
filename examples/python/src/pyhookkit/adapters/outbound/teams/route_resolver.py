"""Logical Teams route resolution from environment-backed configuration."""

from collections.abc import Mapping


class TeamsRouteNotConfiguredError(ValueError):
    """A logical route has no usable Teams Workflow configuration."""


class TeamsEnvironmentRouteResolver:
    """Resolve a logical route through an environment variable name."""

    def __init__(self, route_variables: Mapping[str, str]) -> None:
        self._route_variables = dict(route_variables)

    def resolve(self, route: str, environment: Mapping[str, str]) -> str:
        try:
            variable_name = self._route_variables[route]
        except KeyError as error:
            raise TeamsRouteNotConfiguredError(
                f"Teams route is not configured: {route}"
            ) from error
        workflow_url = environment.get(variable_name, "").strip()
        if not workflow_url:
            raise TeamsRouteNotConfiguredError(
                f"Teams destination variable is empty: {variable_name}"
            )
        return workflow_url
