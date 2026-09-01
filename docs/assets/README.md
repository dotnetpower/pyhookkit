# Documentation assets

Documentation images are organized by the user-facing guide that owns them:

- [`card-previews/`](card-previews/README.md): Slack and Teams client captures
  for paired fundamental examples;
- [`integrated-scenario/`](integrated-scenario/README.md): GitHub, GitLab,
  Argo CD, AKS, Bookinfo, and scenario evidence;
- [`power-automate-teams-workflow/`](power-automate-teams-workflow/README.md):
  redacted Power Automate setup and run-history captures;
- [`logic-app-teams-delivery/`](logic-app-teams-delivery/README.md): redacted
  Logic Apps workflow, security, Teams action, and run-history captures.

Only real client or control-plane captures belong here. Crop images to the
smallest useful region, remove account and environment identities, strip image
metadata, and verify that no URL contains a credential before committing.
