# Container runtime

No standalone PyHookKit container deployment is committed here yet. The
SQLite-backed router can be run as a single process for evaluation, but its
container and persistent-volume composition remain future work.

A future container must receive provider credentials by secret reference,
execute as a non-root user, use a read-only filesystem where practical, define
resource limits and health checks, and avoid logging canonical payloads or
provider responses.

Keep direct GitLab package execution available while evaluating the central
router. Do not run multiple SQLite router replicas against one database file.
