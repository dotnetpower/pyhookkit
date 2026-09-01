# Integration tests

Integration tests exercise composed entrypoints against local mock
destinations; live provider credentials are not required.

This directory is reserved for tests that cross multiple adapters or process
boundaries and cannot be expressed as focused unit or contract tests. A test
belongs here only when it remains deterministic, offline, and safe to run in
CI.

Live Slack, Teams, Azure, GitHub, GitLab, or Argo CD smoke tests are operational
runbook steps, not automated tests in this directory.
