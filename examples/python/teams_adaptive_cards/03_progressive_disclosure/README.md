# T03: Progressive disclosure

Uses `Action.ToggleVisibility` to keep diagnostics out of the default view and
`Action.OpenUrl` for external navigation.

```shell
uv run python teams_adaptive_cards/03_progressive_disclosure/teams.py
uv run python teams_adaptive_cards/03_progressive_disclosure/teams.py --send
```

No server callback is required. Submit or execute actions remain outside the
Workflow webhook capability.
