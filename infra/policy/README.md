# Infrastructure policy

Infrastructure changes must satisfy these policy expectations:

- no plaintext secrets or credential-shaped callback URLs;
- no real account, tenant, subscription, Team, channel, or customer IDs in
  committed examples;
- synthetic parameter files only;
- provider credentials injected by secret reference;
- explicit validation and deletion commands;
- generated state and deployment outputs excluded from Git;
- screenshots cropped and redacted before commit.

Automated repository checks cover schemas, Python types and tests, Bicep,
Kustomize rendering, workflow syntax, and targeted secret patterns. Live
connection authorization and client rendering remain manual verification steps.
