# Azure Bicep

This directory contains a minimal AKS baseline for the Bookinfo GitOps assets
in this repository.

## Files

- `main.bicep` deploys:
  - one virtual network and one AKS subnet
  - one AKS cluster with a single system node pool
  - system-assigned managed identity
  - managed Microsoft Entra integration with Azure RBAC enabled
  - OIDC issuer and workload identity enabled
- `main.parameters.staging.json` provides synthetic staging values only

## Intentional scope

The template keeps the platform surface area small and avoids optional
dependencies:

- no Azure Container Registry
- no ingress controller
- no monitoring add-ons
- no service mesh
- no private endpoints or jump hosts

The cluster uses Azure CNI Overlay plus a standard load balancer for the least
complex network baseline that still supports future workload identity use.
Local administrator credentials remain enabled in the synthetic staging
parameters so an empty Entra group list cannot lock operators out. Configure an
Entra administrator group and Azure Kubernetes Service RBAC role assignments,
verify that access, and then set `disableLocalAccounts` to `true`.

## Deploy

```bash
az group create \
  --name rg-pyhookkit-staging \
  --location koreacentral

az deployment group create \
  --resource-group rg-pyhookkit-staging \
  --template-file infra/azure/bicep/main.bicep \
  --parameters @infra/azure/bicep/main.parameters.staging.json
```

## Connect and apply Bookinfo

```bash
az aks get-credentials \
  --resource-group rg-pyhookkit-staging \
  --name phk-aks-stg-82001 \
  --admin

kubectl apply -k infra/gitops/bookinfo/overlays/staging
```

## Post-deploy checks

```bash
az aks show \
  --resource-group rg-pyhookkit-staging \
  --name phk-aks-stg-82001 \
  --query '{oidcEnabled:oidcIssuerProfile.enabled, oidcIssuer:oidcIssuerProfile.issuerUrl, workloadIdentity:securityProfile.workloadIdentity.enabled}'

kubectl -n bookinfo-staging get deploy,svc,job
```

`main.parameters.staging.json` intentionally uses synthetic names, object IDs,
and tags. Replace them only at deploy time if your environment needs different
values.
