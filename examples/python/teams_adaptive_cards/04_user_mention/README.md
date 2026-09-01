# T04: User mention

Demonstrates matching `<at>` text and a Teams mention entity.

```shell
uv run python teams_adaptive_cards/04_user_mention/teams.py
uv run python teams_adaptive_cards/04_user_mention/teams.py --send
```

Live delivery requires `TEAMS_TEST_USER_ID` and `TEAMS_TEST_USER_NAME`. The
display name must not contain `<`, `>`, or `&`, and the committed card keeps
only synthetic replacement markers.
