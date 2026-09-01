# Control-plane integrations

These adapters connect source control, CI, and continuous delivery without
moving provider credentials into every platform:

- [`github/`](github/README.md) owns protected release approval;
- [`gitlab/`](gitlab/README.md) owns validation, promotion, and notification
  dispatch;
- [`argocd/`](argocd/README.md) owns AKS reconciliation and deployment-result
  events.

Canonical notification JSON crosses integration boundaries. Slack or Teams
payload rendering occurs only at the configured delivery job.

Use a distinct, revocable credential for each producer. Never put a token in a
committed URL, Argo CD Application, pipeline input, screenshot, or log.
