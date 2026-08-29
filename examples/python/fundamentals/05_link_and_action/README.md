# F05: Link and action

Canonical HTTPS links become Slack `button` elements. Only navigation is in
scope; interactive callbacks require a separately authenticated endpoint.

Teams renders the same navigation as `Action.OpenUrl` in an Adaptive Card.
Neither provider requires an interactive callback or additional permission for
this navigation-only action.

The Teams example follows the Adaptive Cards edge-to-edge guidance: its
theme-aware `accent` call-to-action container uses `bleed: true` to extend to
the card edges and contains one concise instruction plus a centered `ActionSet`.
This separates the safe navigation step without duplicating labels or changing
the canonical action.

```shell
python fundamentals/05_link_and_action/slack.py
python fundamentals/05_link_and_action/teams.py
```
