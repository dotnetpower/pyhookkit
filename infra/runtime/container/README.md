# Container runtime

The committed container runs one non-root SQLite-backed router instance with a
persistent volume, read-only root filesystem, dropped Linux capabilities, and
an HTTP health check.

From the repository root, create the ignored `.env`, then run:

```shell
docker compose -f infra/runtime/container/docker-compose.yml up --build -d
```

The Compose file publishes the API on loopback only at `127.0.0.1:8080`.
Configure destinations, producer API keys, and inbound integrations before
placing an HTTPS API gateway in front of it. Commands can run against the same
volume through the router container, for example:

```shell
docker compose -f infra/runtime/container/docker-compose.yml exec router \
	python -m pyhookkit.entrypoints.notification_router \
	--database /data/router.sqlite3 \
	list-integrations
```

Do not publish `/admin`. Run the administration process on an operator host
with loopback binding and controlled access to the same database, or perform
configuration through one-shot container commands while the router is stopped.

For internet-facing provider webhooks, terminate TLS at an API gateway and
publish only:

- `/healthz` to an internal health probe;
- `/v1/notifications` and `/v1/destinations/*/notifications` to authorized CI
	producers;
- `/v1/inbound/*` to configured provider webhooks.

`gateway.nginx.conf` is a reference allowlist and rate-limit configuration. It
expects the router at `router:8080` and certificate files mounted as
`/run/secrets/tls_certificate` and `/run/secrets/tls_private_key`. It is not
enabled by the local Compose file because certificate issuance and public DNS
ownership belong to the deployment environment.

Apply request-size limits and rate limits at the gateway. Never run multiple
router replicas against one SQLite file. Move the outbox and integration
configuration to a managed transactional database or queue before scaling
horizontally.
