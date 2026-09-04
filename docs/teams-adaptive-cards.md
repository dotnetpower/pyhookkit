# Teams Adaptive Card design

[한국어](teams-adaptive-cards.ko.md)

PyHookKit targets Adaptive Card 1.4 for Teams Workflow delivery. Teams currently
supports newer schema versions, but the conservative baseline reduces
differences across web, desktop, mobile, and embedded surfaces.

The implementation follows the official
[Adaptive Cards design best practices](https://adaptivecards.microsoft.com/?topic=design-best-practices)
and the
[Teams card reference](https://learn.microsoft.com/microsoftteams/platform/task-modules-and-cards/cards/cards-reference).

## Design baseline

- Put the outcome and primary title first.
- Use size, weight, semantic color, and spacing to establish hierarchy.
- Keep the default view concise; use progressive disclosure for diagnostics.
- Use no fixed card or column widths and no more than three columns. PyHookKit
  uses at most two flexible columns.
- Include `fallbackText` and `speak` summaries.
- Give every image meaningful `altText`.
- Host images on a public HTTPS CDN. Use PNG, JPEG, or GIF, no larger than
  1024 x 1024 pixels and 1 MB. Avoid redirects and SVG.
- Prefer Markdown over HTML in `TextBlock`. Teams supports only a subset, so do
  not rely on Markdown headers, tables, images, preformatted text, or
  blockquotes.
- Use a small number of specific, clearly labeled actions.
- Verify both wide desktop and narrow mobile layouts.

The Workflow gallery permits only the actions verified with its Flow bot host:
`Action.OpenUrl` and `Action.ToggleVisibility`. `Action.Submit`,
`Action.Execute`, and other actions requiring server-side state need an
appropriate bot or another authenticated adapter and aren't accepted by the
gallery validation.

## Gallery

Provider-specific examples are under
`examples/python/teams_adaptive_cards`.

| ID | Pattern | Elements demonstrated |
|---|---|---|
| T00 | Visual hierarchy | Emoji header, semantic color, concise callout |
| T01 | Metrics dashboard | Flexible two-column metric tiles |
| T02 | Hero image | Responsive image, alt text, caption, fallback |
| T03 | Progressive disclosure | `Action.ToggleVisibility` and `Action.OpenUrl` |
| T04 | User mention | `<at>` text and Teams mention entity |
| T05 | Progress timeline | Completed, active, and pending visual states |
| T06 | Image gallery | Three attributed, repository-hosted sample images |

Render a card from `examples/python`:

```shell
uv run python teams_adaptive_cards/01_metrics_dashboard/teams.py
```

Send it through the configured from-blank Workflow:

```shell
uv run python teams_adaptive_cards/01_metrics_dashboard/teams.py --send
```

Image-led examples require `EXAMPLE_ASSET_BASE_URL` when sending; the existing
`TEAMS_ASSET_BASE_URL` name remains a compatible fallback. Point it at the
published `teams_adaptive_cards/assets` directory through a direct HTTPS CDN or
GitHub raw URL. T04 requires `TEAMS_TEST_USER_ID` and
`TEAMS_TEST_USER_NAME`. These runtime values belong in the ignored `.env` or an
approved secret/configuration store, never in fixtures.
The display name must be plain text without `<`, `>`, or `&` because the same
value must match the Adaptive Card `<at>` token and Teams mention entity.

The committed cat images come from the MicrosoftDocs/AdaptiveCards repository
under CC BY 4.0. Their source paths, modifications, and license link are in the
[asset attribution](../examples/python/teams_adaptive_cards/assets/ATTRIBUTION.md).
The editorial hero is redistributed unchanged from the official
OfficeDev/Microsoft-Teams-Adaptive-Card-Samples repository under the MIT License.

## Workflow attribution

Card design does not control the Teams **Get template** footer. Gallery-template
flows retain an **Original template** relationship and receive the footer
outside the Adaptive Card payload. Use the verified from-blank flow in the
[Power Automate Teams Workflow guide](power-automate-teams-workflow.md) when
attribution must be absent.

## Verification

Automated tests enforce:

- one valid Adaptive Card attachment per Teams message envelope;
- Adaptive Card 1.4;
- non-empty `fallbackText` and `speak`;
- no fixed column widths;
- no more than three columns;
- HTTPS images with non-empty `altText`;
- only supported webhook action types;
- no more than three top-level actions.

Live verification remains necessary for image retrieval, mentions, button
behavior, mobile layout, and host-specific rendering.
