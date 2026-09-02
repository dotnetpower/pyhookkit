# Teams Workflows

This directory owns reusable Workflow templates and the owner, connection, and
callback URL bootstrap runbook.

The user-facing [Power Automate Teams Workflow
guide](../../docs/power-automate-teams-workflow.md) contains the from-blank
creation steps, screenshots, callback storage, and smoke test. This runbook
focuses on provider lifecycle, repeat deployment, and attribution verification.

## Production identity model

Keep flow ownership, connector authentication, and runtime invocation as three
separate security boundaries:

| Boundary | Identity | Required access |
|---|---|---|
| Solution-aware flow owner | Dataverse application user for an Entra service principal | Own and activate the imported flow |
| Teams connection | Dedicated licensed Microsoft 365 user | Member of the destination Team and any required private or shared channel |
| Runtime caller | CI/CD or workload identity | Possession of the signed Workflow callback URL only |
| Operations | At least two named administrators | Co-owner access for recovery and connection reauthorization |

The Teams connector's default authentication is a non-shareable user OAuth
connection. Assigning the flow to a service principal does not convert that
connection to application authentication. Do not share the dedicated user's
password. Restrict interactive access, apply Conditional Access appropriate to
the connector authorization flow, and monitor license, sign-in, and connection
health separately from flow ownership.

Do not grant the dedicated user a tenant administrator role. Team membership is
sufficient for a standard destination channel. Private and shared channels are
visible only when the user is a member, and the Teams connector does not
currently support posting messages or Adaptive Cards to private channels.

### Authorization boundaries

Ownership and execution permissions are deliberately non-transitive:

- assigning the Dataverse application user as flow owner does not authorize a
  Teams connection for that principal;
- binding a connection reference selects an existing connection but does not
  copy, share, or convert the connection user's OAuth credentials;
- adding a co-owner permits flow administration but does not let that person
  edit credentials for a connection created by another user;
- possession of the signed callback URL permits invocation but grants no
  Power Platform, Teams, or Graph role;
- granting Graph channel-read permission to an inventory principal does not
  authorize Teams connector delivery.

The detailed role setup, runtime sequence, and recovery behavior are in the
[Power Automate Teams Workflow guide](../../docs/power-automate-teams-workflow.md#identity-and-permission-setup).

## Quick template bootstrap

The quickest bootstrap uses a one-time manually created Teams Workflow:

1. Open **Workflows** from the target Teams channel.
2. Search for `webhook`.
3. Select **Send webhook alerts to a channel**.
4. Choose the Microsoft connection, Team, and test Channel.
5. Save the Workflow and copy its generated HTTP POST URL.
6. Store the URL as `TEAMS_WORKFLOW_URL` in the ignored repository `.env`.

The generic channel template is required by the current unauthenticated
callback client. Do not select the templates restricted to specific people or
people in the organization unless an authenticated Teams adapter is added.

Cards sent by this template display an attribution footer containing the
Workflow owner and a **Get template** link. Teams injects the footer outside the
Adaptive Card JSON. Changing the payload, including switching from plain text
to a rich card, does not remove it.

The attribution is tied to the flow's template origin:

- the template-created flow's Power Automate details page shows an
  **Original template** relationship;
- its Teams footer links back to that same template;
- the from-blank flow has no **Original template** relationship and produces no
  attribution footer while using the same trigger, Teams connector action, and
  Adaptive Card envelope.

This is the discoverability behavior announced in
[Microsoft 365 Roadmap 393923](https://www.microsoft.com/microsoft-365/roadmap?featureid=393923).
It is flow metadata, not an Adaptive Card element.

## Attribution-free flow created from blank

Create and test this flow by following the
[Power Automate Teams Workflow guide](../../docs/power-automate-teams-workflow.md).

Live verification showed that this from-blank flow renders titles, severity
colors, facts, buttons, and native user mentions without the owner attribution
or **Get template** link. This behavior is verified for the current Teams and
Power Automate versions but is not a documented Microsoft guarantee.

After creating or copying a flow, open its Power Automate details page. Treat a
visible **Original template** link as an attribution risk and run a channel
smoke test before promoting its callback URL. **Save As** is not considered a
reliable workaround because copy behavior can preserve or recreate template
metadata; creating from blank is the reproducible path verified here.

## Automated deployment

The Power Automate portal is not required for repeated deployments after a
from-blank flow has been authored once. The supported ALM path is to store the
flow inside a Power Platform Solution and deploy the Solution with Power
Platform CLI.

The checked-in tools automate the supported lifecycle after a from-blank flow
has been authored and exported as a Solution:

1. add the verified from-blank flow to an unmanaged Solution;
2. replace its concrete Teams connection with a connection reference;
3. represent the exact approved channel links with one environment variable;
4. authenticate Power Platform CLI with an approved service principal;
5. export and unpack the unmanaged Solution as the source artifact;
6. pack and import the Solution into the target environment;
7. bind the target connection reference and environment variables;
8. activate the imported flow;
9. assign and verify the Dataverse application user as flow owner;
10. optionally inventory the channels visible through Microsoft Graph;
11. retrieve the HTTP trigger callback URL and write it directly to the target
    secret store;
12. run a synthetic rich-card smoke test and assert that the posted card has no
    template attribution.

Steps 1-3 and the first Teams OAuth authorization are one-time environment
bootstrap operations. The flow must contain exactly one
`/providers/Microsoft.PowerApps/apis/shared_teams` connection reference and the
`pyk_AllowedChannelLinks` text environment variable. Its current value is a
JSON array of exact Teams channel links.

Authenticate `pac` before running the deployment. In CI, inject the client
secret from the approved secret store; never place it in a repository file or
shell history:

```shell
pac auth create \
  --name pyhookkit-production \
  --applicationId "$POWER_PLATFORM_APPLICATION_ID" \
  --clientSecret "$POWER_PLATFORM_CLIENT_SECRET" \
  --tenant "$POWER_PLATFORM_TENANT_ID"
```

The service principal must already exist as a Dataverse application user in
the target environment. Use the narrowest role that can import the Solution,
activate its flow, and assign the Process row. Do not retain the default System
Administrator role after bootstrap.

Before the first production deployment, verify each permission independently:

| Check | Principal | Evidence |
|---|---|---|
| Power Platform authentication and Solution import | Deployment service principal | `pac auth list` succeeds and a synthetic managed import completes |
| Enabled application user and flow ownership | Dataverse application user | `set-flow-owner.py verify` exits successfully for the imported flow |
| Teams connection binding | Dedicated connection user | The connection reference resolves to a valid Microsoft Teams connection in the target environment |
| Destination access | Dedicated connection user | The approved standard channel is visible to the user and receives a synthetic card |
| Optional channel inventory | Graph delegated or application principal | `list-team-channels.py` writes the expected access-scoped `0600` report |
| Runtime invocation | CI/CD or workload identity | It can read the callback secret and the allowlisted channel link, but has no connection-user credentials |
| Operational recovery | Two named administrators | Both appear as co-owners and can inspect run history without assuming the connection user's account |

Run the checks again after replacing a connection user, changing a Dataverse
role, changing Team membership, importing into another environment, or rotating
the callback URL. A successful owner check does not prove Teams delivery; the
live card smoke test is a separate required check.

A service principal application user cannot hold a user license. If the flow
uses premium features, assign a Power Automate Process license to the
solution-aware flow or designate a sufficiently licensed human co-owner on the
flow details page. A standard-connector-only flow remains subject to the
tenant's non-licensed request pool; monitor that pool rather than assuming the
dedicated Teams connection user's license transfers to the flow owner.

Run the deployment from the repository root after injecting the Dataverse and
Graph access tokens into the environment. The scripts never pass either token
as a command argument. Set `SOLUTION_FOLDER` to the checked-in output of
`pac solution clone` or `pac solution unpack`; this repository does not
fabricate the environment-specific initial flow definition:

```shell
mkdir -p infra/teams-workflows/.local

infra/teams-workflows/bin/deploy-solution.sh \
  --solution-folder "$SOLUTION_FOLDER" \
  --solution-zip infra/teams-workflows/.local/pyhookkit-teams.zip \
  --package-type Managed \
  --environment "https://example.crm.dynamics.com" \
  --teams-connection-id "$TEAMS_CONNECTION_ID" \
  --allowed-channel-links-schema-name pyk_AllowedChannelLinks \
  --allowed-channel-link "$TEAMS_WORKFLOW_CHANNEL_LINK" \
  --flow-id "$TEAMS_FLOW_ID" \
  --application-id "$POWER_PLATFORM_APPLICATION_ID" \
  --inventory-team-id "$TEAMS_TEAM_ID" \
  --channel-report infra/teams-workflows/.local/channels.json \
  --include-incoming \
  --smoke-test
```

`prepare-deployment-settings.py` rejects missing or duplicate Teams connection
references, missing allowlist variables, duplicate or invalid channel links,
and signed URLs. Repeat `--allowed-channel-link` for every approved notification
destination; each link is stored in the environment variable as one JSON
array.
`set-flow-owner.py` resolves exactly one enabled Dataverse application user,
updates the flow `ownerid`, and reads it back. `list-team-channels.py` requests
only `id`, `displayName`, and `membershipType`, follows Graph pagination, and
writes the report with mode `0600`. `--smoke-test` sends the synthetic
deployment-result scenario through `TEAMS_WORKFLOW_URL` and fails unless the
redacted delivery result succeeds. Retrieve that URL through the supported
administrative procedure for the target environment and inject it from the
secret store; the deployment script never prints it or writes it to disk.

For a delegated token, grant `Channel.ReadBasic.All`; the report then reflects
only private and shared channels visible to the signed-in user. For an
application token, prefer Team-scoped resource-specific consent
`ChannelSettings.Read.Group` with the `/channels` endpoint. Use tenant-wide
application `Channel.ReadBasic.All` only when the application must inventory
more than the consented Team. The `--include-incoming` option calls
`/allChannels`, requires application `Channel.ReadBasic.All`, and includes
incoming shared channels. Add application `Team.ReadBasic.All` only when Team
discovery is required; this tooling accepts a configured Team ID and does not
need it.

The automation does not assume that Microsoft connection consent is portable.
Initial connection authorization, tenant policy approval, and Workflow
ownership may remain environment bootstrap steps. The generated callback URL is
environment-specific runtime state and must never be committed to a Solution
package or repository file.

Power Platform CLI supports Solution export, unpack, pack, and import, but it is
not a step-level cloud-flow designer. Creating the first flow entirely from raw
Dataverse `workflow` and `clientdata` records is possible through the Dataverse
Web API, but is intentionally not recommended here because those definitions
are complex and platform-version-sensitive.

The recommended boundary is therefore:

- **one-time authoring:** create and verify the from-blank flow;
- **source control:** keep the unpacked Solution, excluding credentials and
  generated callback URLs;
- **repeat deployment:** use Power Platform CLI and management APIs without
  opening the portal;
- **environment bootstrap:** authorize the Teams connection when tenant policy
  requires an interactive administrator or owner.

Before upgrading the tooling, confirm the current
[Power Platform CLI Solution commands](https://learn.microsoft.com/power-platform/developer/cli/reference/solution),
[cloud-flow code APIs](https://learn.microsoft.com/power-automate/manage-flows-with-code),
and Teams Workflow behavior because callback URL lifecycle and connector
retirement dates can change.

## Footer verification checklist

The gallery-template footer problem must be checked independently of card
rendering:

1. On the flow details page, confirm that **Original template** is absent.
2. Confirm the trigger is **When an HTTP request is received** with the routed
  request schema.
3. Confirm an exact `pyk_AllowedChannelLinks` check precedes URL parsing and the
  Teams connector action.
4. Confirm the action uses the request Team and Channel IDs derived from the
  validated link and passes only
  `first(triggerBody()?['attachments'])?['content']` as the Adaptive Card.
5. Retrieve a fresh callback URL after deployment instead of copying one from a
   different environment.
6. Send a synthetic card containing a title, `FactSet`, and `Action.OpenUrl`.
7. Inspect the posted card and confirm that neither the owner attribution nor
   **Get template** appears.

Changing the Adaptive Card JSON, flow name, owner, or callback URL does not
remove attribution from a flow that retains an **Original template**
relationship. Recreating the flow from blank is the verified remedy.
