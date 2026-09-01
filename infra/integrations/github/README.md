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
4. Store both URL forms as repository Actions secrets:

   ```text
   GITLAB_WEBHOOK_URL=https://gitlab.example.com/api/v4/projects/123456/ref/main/trigger/pipeline?token=<token>
   GITLAB_TRIGGER_URL=https://gitlab.example.com/api/v4/projects/123456/trigger/pipeline?token=<token>&ref=main
   ```

The URLs are credentials. Do not print them, commit them, place them in a
repository variable, or include them in a notification. The webhook form
preserves canonical JSON as GitLab's `TRIGGER_PAYLOAD`; the API form accepts
typed promotion inputs. GitLab alone owns the Teams Workflow callback URL.

The approval card links to the GitHub Actions run. GitHub's native environment
review remains the source of truth; the Teams button does not approve a
deployment by itself.
