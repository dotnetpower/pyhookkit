# Container runtime

No standalone PyHookKit container deployment is committed here yet.

A future container must receive provider credentials by secret reference,
execute as a non-root user, use a read-only filesystem where practical, define
resource limits and health checks, and avoid logging canonical payloads or
provider responses.

Do not build a long-running notification service merely to execute the current
examples; GitLab invokes the Python package directly.
