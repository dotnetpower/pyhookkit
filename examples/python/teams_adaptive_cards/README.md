# Teams Adaptive Card gallery

These Teams-only examples demonstrate presentation patterns that are more
specific than the provider-neutral notification contract. Each directory
contains a standalone `card.json` and a thin `teams.py` runner.

From `examples/python`, render any card:

```shell
uv run python teams_adaptive_cards/00_visual_hierarchy/teams.py
```

After loading the repository `.env`, add `--send` to post through the
footer-free, from-blank Workflow:

```shell
uv run python teams_adaptive_cards/00_visual_hierarchy/teams.py --send
```

| ID | Pattern | Best-practice focus |
|---|---|---|
| T00 | Visual hierarchy | Critical content first, concise header and callout |
| T01 | Metrics dashboard | Two-column responsive metrics without fixed widths |
| T02 | Hero image | Public CDN image, alt text, caption and fallback |
| T03 | Progressive disclosure | Limited actions and in-card detail toggle |
| T04 | User mention | Teams mention entity with runtime-only identity |
| T05 | Progress timeline | Scannable status sequence and current-step emphasis |
| T06 | Image gallery | Three attributed repository-hosted sample images |

The gallery targets Adaptive Card 1.4 for conservative Workflow compatibility.
It avoids fixed pixel widths and keeps ColumnSets to two columns. Newer
responsive features such as `targetWidth` are intentionally excluded until the
minimum Teams host version is raised and mobile rendering is verified.

T02 and T06 require `TEAMS_ASSET_BASE_URL` with `--send`. After the assets are
published to the default branch, configure:

```dotenv
TEAMS_ASSET_BASE_URL="https://raw.githubusercontent.com/dotnetpower/pyhookkit/main/examples/python/teams_adaptive_cards/assets"
```

The base URL must serve the committed PNG files directly over HTTPS without a
redirect. T04 requires `TEAMS_TEST_USER_ID` and `TEAMS_TEST_USER_NAME` only with
`--send`. Never commit runtime URLs or account identifiers.

The three cat images are redistributed from MicrosoftDocs/AdaptiveCards under
CC BY 4.0. See `assets/ATTRIBUTION.md`.
