# Getting started

## Local provider configuration

Create the ignored local configuration file:

```shell
cp .env.example .env
```

Fill in `SLACK_WEBHOOK_URL` and `TEAMS_WORKFLOW_URL` as described in
[Provider configuration](configuration.md). The initial render-only examples
can run while these values are blank.

## Run without installing PyHookKit

The F00 bootstrap example uses only Python's standard library to show the raw
provider HTTP requests:

```shell
cd examples/python
python fundamentals/00_http_request/slack.py
python fundamentals/00_http_request/teams.py
```

The commands render provider payloads by default. After loading `.env`, add
`--send` to deliberately deliver one of them.

## Run the PyHookKit paired example

The first library-backed example is under
`examples/python/fundamentals/01_hello_world`.

Install the Python development dependencies from `examples/python`, then run
the paired Slack and Teams scripts. The examples use synthetic payloads and do
not require live credentials.

```shell
cd examples/python
uv sync --extra dev --python 3.12
uv run python fundamentals/01_hello_world/slack.py
uv run python fundamentals/01_hello_world/teams.py
```

Slack F01-F07 and F10 also accept `--send` after `.env` is loaded. See
[Slack examples](slack-examples.md) before sending mention, thread, or mutation
examples.
