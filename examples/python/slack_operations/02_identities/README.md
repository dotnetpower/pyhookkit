# O02: Identity discovery

Resolves one active non-bot member by display name and lists mentionable Slack
user groups.

```shell
uv run python slack_operations/02_identities/slack.py
uv run python slack_operations/02_identities/slack.py \
  --live --display-name example-owner
```

Add `--send-mention` only after confirming an exact unique match and
`SLACK_CHANNEL_ID`. Live calls require `users:read`, `usergroups:read`, and
`chat:write` when sending. The example does not request email addresses.
