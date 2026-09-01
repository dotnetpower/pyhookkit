# Azure parameters

Committed parameter files contain deployable synthetic defaults only.

- [`example/`](example/README.md) documents the parameter policy.
- [`../bicep/main.parameters.staging.json`](../bicep/main.parameters.staging.json)
  is the synthetic staging input for the AKS template.

Supply real environment values at deployment time or through an approved
private parameter store. Do not commit subscription, tenant, Entra group,
network, connection, or callback values copied from a live environment.
