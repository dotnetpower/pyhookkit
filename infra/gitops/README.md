# GitOps assets

GitOps assets describe workloads reconciled by Argo CD. The current example is
the Istio-free [`bookinfo/`](bookinfo/README.md) staging application.

The Git repository is the desired-state boundary:

- GitLab validates and updates the protected GitOps branch;
- Argo CD reads that branch and reconciles AKS;
- runtime secrets are injected separately and never stored in overlays;
- PostSync hooks prove workload health before deployment success is reported.

Keep reusable workload resources in a base and environment policy in overlays.
Do not commit generated manifests, cluster credentials, live destination URLs,
or imperative state.
