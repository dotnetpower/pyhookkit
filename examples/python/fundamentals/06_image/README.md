# F06: Image

Adds a public HTTPS image and mandatory alt text. Slack and Teams display the
alt text when the image cannot be loaded; delivery success does not prove image
availability. The committed image URL is synthetic. Live Slack delivery and
either Teams delivery option replace it from `EXAMPLE_ASSET_BASE_URL`;
`TEAMS_ASSET_BASE_URL` remains a compatible fallback for existing local
configuration. The image is the unchanged Microsoft Teams Adaptive Card recipe
sample documented in the repository's third-party notices.
