# Bookinfo GitOps

This tree provides a minimal Istio-free Bookinfo deployment for AKS.

## Layout

- `base/` contains namespace, services, and deployments
- `overlays/staging/` renames the namespace to `bookinfo-staging`, scales the
  user-facing path slightly, pins the active Reviews variant, and adds an
  internal smoke-test Job
- `bin/set-staging-reviews.sh` switches only the active Reviews patch in the
  staging overlay

## Images

Bookinfo container images are pinned to `1.20.2` tags from
`docker.io/istio/examples-bookinfo-*`. The smoke test image is pinned to
`curlimages/curl:8.10.1`.

## Apply

```bash
kubectl apply -k infra/gitops/bookinfo/overlays/staging
```

## Switch the staging Reviews variant

```bash
infra/gitops/bookinfo/bin/set-staging-reviews.sh v1
infra/gitops/bookinfo/bin/set-staging-reviews.sh v2
infra/gitops/bookinfo/bin/set-staging-reviews.sh v3
```

The script updates only:

- `infra/gitops/bookinfo/overlays/staging/kustomization.yaml`

It swaps the active file reference among:

- `infra/gitops/bookinfo/overlays/staging/reviews-v1-patch.yaml`
- `infra/gitops/bookinfo/overlays/staging/reviews-v2-patch.yaml`
- `infra/gitops/bookinfo/overlays/staging/reviews-v3-patch.yaml`

After changing the variant, apply the staging overlay again:

```bash
kubectl apply -k infra/gitops/bookinfo/overlays/staging
```

## Smoke test

The staging overlay creates `Job/bookinfo-smoke`. It waits for
`http://productpage:9080/productpage` to return a page containing
`BookInfo Sample`. Argo CD runs it as a `PostSync` hook for every promoted
revision and removes it after success.

## Synthetic incident

The one-time `operations/incident-probe-job.yaml` requests an intentionally
invalid productpage path and sends a canonical incident event through GitLab.
It does not alter the Bookinfo deployment or require a monitoring stack.

Create a dedicated GitLab trigger token, then inject its complete URL directly
into a Kubernetes Secret:

```bash
kubectl -n bookinfo-staging create secret generic gitlab-notification-trigger \
  --from-literal=url="$GITLAB_TRIGGER_URL"
kubectl apply -f infra/gitops/bookinfo/operations/incident-probe-job.yaml
kubectl -n bookinfo-staging wait \
  --for=condition=complete job/bookinfo-incident-probe \
  --timeout=2m
```

Replace the synthetic `INCIDENT_URL` and `RUNBOOK_URL` values before a live
demonstration. The incident action opens GitLab's new-issue page; creating or
updating that issue is the acknowledgment system of record. Delete and recreate
the Job for another deliberate run.

## One-time migration note

Earlier drafts used a `Deployment/reviews-v3` resource name. The current tree
uses a stable `Deployment/reviews` name so GitLab promotion only changes the
staging variant patch. If a cluster already has the old resource, delete it
once after applying the current staging overlay:

```bash
kubectl -n bookinfo-staging delete deployment reviews-v3 --ignore-not-found
```
