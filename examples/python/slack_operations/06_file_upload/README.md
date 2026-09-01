# O06: File upload

Uploads a synthetic CSV with Slack's current external upload sequence:
`files.getUploadURLExternal`, binary upload, then
`files.completeUploadExternal`.

```shell
uv run python slack_operations/06_file_upload/slack.py
uv run python slack_operations/06_file_upload/slack.py --upload
```

The live command requires `files:write` and `SLACK_CHANNEL_ID`. It creates a
real Slack file and does not delete it automatically.
