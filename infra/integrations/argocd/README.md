# Argo CD integration

Argo CD owns Bookinfo deployment reconciliation. It watches the GitLab GitOps
repository, deploys the staging overlay to AKS, and submits canonical deployment
results to a GitLab trigger pipeline. GitLab renders and delivers the result;
Argo CD does not contain a provider-specific Teams payload.

## Bootstrap

1. Install the pinned Argo CD chart with the minimal single-node values:

   ```shell
   helm repo add argo https://argoproj.github.io/argo-helm
   helm repo update argo
   helm upgrade --install argocd argo/argo-cd \
     --version 10.4.2 \
     --namespace argocd \
     --create-namespace \
     --values infra/integrations/argocd/values.yaml \
     --wait \
     --timeout 10m
   ```

   The example does not use SSO or ApplicationSets, so Dex is disabled and the
   ApplicationSet controller has zero replicas. This leaves enough Pod capacity
   for Bookinfo hooks on the one-node AKS baseline.
2. Give Argo CD read-only access to the GitLab GitOps repository with a deploy
   key.
3. Create the protected `gitops-staging` branch and replace the synthetic
   `repoURL` in `application.yaml`.
4. Replace `context.argocdUrl` in `notifications-config.yaml` with the public
   HTTPS Argo CD URL used by operators.
5. Create a GitLab project access token with the `api` scope and Maintainer
   access. Give it the shortest practical expiration. Replace the synthetic
   project ID and GitLab host in `notifications-config.yaml`.

6. Create the notification secret without writing the URL to disk:

   ```shell
   kubectl -n argocd create secret generic argocd-notifications-secret \
     --from-literal=gitlab-api-token="$GITLAB_API_TOKEN"
   ```

7. Apply `notifications-config.yaml` and `application.yaml`.

Do not apply `notifications-secret.example.yaml`; it documents only the required
key. The API token is a credential and must stay out of Git, terminal output,
service URLs, and Argo CD Application resources. The webhook service submits it
in the `PRIVATE-TOKEN` header so controller logs contain only the non-sensitive
pipeline endpoint.

The custom triggers fire once per reconciled revision. The template submits
canonical JSON through the `CANONICAL_NOTIFICATION` pipeline variable. GitLab
validates it and sends it through the configured provider adapter.

`context.teamsDelivery` selects `workflow` (default) or `logic-app` for
deployment-result notifications. Configure the corresponding protected GitLab
variables before choosing Logic App.

The committed Application uses automated prune and self-heal for a disposable
staging namespace. Use a separate Argo CD Project and a manual promotion policy
before adapting this example to a shared or production cluster.
