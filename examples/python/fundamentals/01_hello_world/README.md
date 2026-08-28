# F01: Hello World

This example renders one canonical notification into paired Slack text and
Teams Adaptive Card payloads. Rendering does not require credentials.

From `examples/python`:

```shell
python fundamentals/01_hello_world/slack.py
python fundamentals/01_hello_world/teams.py
```

After loading the repository `.env`, add `--send` to the Slack command to
deliberately deliver the message through the configured Incoming Webhook. The
Teams command also accepts `--send` and uses `TEAMS_WORKFLOW_URL`.

Both scripts use `example_notification.py`. Provider-specific rendering remains
under `src/pyhookkit/adapters/outbound`.
