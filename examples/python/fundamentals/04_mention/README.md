# F04: Mention

The shared canonical case contains logical user and group aliases. Slack
resolves both to native mentions. The Teams example renders only the native user
mention and intentionally omits the group alias from the card.

The committed mappings are synthetic. A real Slack user ID starts with `U` or
`W`, while a Slack user-group ID starts with `S`. Set `SLACK_USER_ID` and
`SLACK_USER_GROUP_ID` before Slack live delivery.

Teams resolves the user alias to an Adaptive Card mention entity. Set
`TEAMS_TEST_USER_ID` and `TEAMS_TEST_USER_NAME` before Teams live delivery.
Basic Workflow delivery needs no Graph permission.

Distribution-list notification is intentionally outside this fundamental case.
It requires additional configuration that resolves members through Microsoft
Graph and renders each member as an individual mention. That advanced adapter
requires application credentials, administrator consent for
`GroupMember.Read.All`, and a policy for membership and card-size limits.

```shell
python fundamentals/04_mention/slack.py
python fundamentals/04_mention/teams.py
```
