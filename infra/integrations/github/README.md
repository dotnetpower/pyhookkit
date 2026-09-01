# GitHub release approval

GitHub owns the human approval boundary for the Bookinfo staging scenario. The
[`bookinfo-release.yml`](../../../.github/workflows/bookinfo-release.yml)
workflow sends a provider-neutral approval request to GitLab, waits at the
`bookinfo-staging` environment, and asks GitLab to promote the approved Reviews
variant.

## Repository configuration

1. Create the `bookinfo-staging` GitHub environment.
2. Add the required reviewers and prevent self-review when the repository plan
   supports that protection rule.
3. Create a GitLab pipeline trigger token scoped to the GitLab project.
4. Store the trigger API URL as the repository Actions secret:

   ```text
   GITLAB_TRIGGER_URL=https://gitlab.example.com/api/v4/projects/123456/trigger/pipeline?token=<token>&ref=main
   ```

The URL is a credential. Do not print it, commit it, place it in a repository
variable, or include it in a notification. GitHub submits the canonical JSON as
the `CANONICAL_NOTIFICATION` trigger variable and uses typed inputs for
promotion. GitLab alone owns the Teams Workflow callback URL.

The approval card links to the GitHub Actions run. GitHub's native environment
review remains the source of truth; the Teams button does not approve a
deployment by itself.
