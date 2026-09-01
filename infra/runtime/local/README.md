# Local runtime

Local development uses synthetic fixtures and render-only commands by default.
Provider credentials may exist only in the ignored repository `.env`.

Unit and integration tests use injected transports or local mock destinations;
they do not call live Slack, Teams, GitLab, or Azure endpoints.

See [`../../../docs/getting-started.md`](../../../docs/getting-started.md) for
installation and [`../../../docs/configuration.md`](../../../docs/configuration.md)
for local variables.
