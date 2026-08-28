"""Logical Slack route resolution from environment-backed configuration."""

from collections.abc import Mapping


class SlackRouteNotConfiguredError(ValueError):
    """A logical route has no usable Slack webhook configuration."""


class SlackEnvironmentRouteResolver:
    """Resolve a logical route through an environment variable name."""

    def __init__(self, route_variables: Mapping[str, str]) -> None:
        self._route_variables = dict(route_variables)

    def resolve(self, route: str, environment: Mapping[str, str]) -> str:
        try:
            variable_name = self._route_variables[route]
        except KeyError as error:
            raise SlackRouteNotConfiguredError(
                f"Slack route is not configured: {route}"
            ) from error
        webhook_url = environment.get(variable_name, "").strip()
        if not webhook_url:
            raise SlackRouteNotConfiguredError(
                f"Slack destination variable is empty: {variable_name}"
            )
        return webhook_url
