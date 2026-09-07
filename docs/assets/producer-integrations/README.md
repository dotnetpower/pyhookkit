# Producer integration captures

[한국어](README.ko.md)

These captures document provider configuration using synthetic endpoints and
credentials. They do not show account navigation, organization identity, or a
saved live Webhook.

| File | Purpose |
|---|---|
| `github-webhook-settings.png` | GitHub Add webhook form with a synthetic inbound URL, JSON content type, synthetic secret, SSL verification, and individual-event selection |
| `github-actions-secret.png` | Unsaved GitHub Actions repository secret form using a synthetic router API key |
| `github-webhook-success.png` | Sanitized GitHub Webhook list showing a successful live ping delivery through a temporary HTTPS tunnel |

Crop captures to the smallest useful form area, use only synthetic values,
strip metadata, and never save a provider integration solely for documentation.
