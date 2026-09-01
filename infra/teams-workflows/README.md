# Teams Workflows

This directory owns reusable Workflow templates and the owner, connection, and
callback URL bootstrap runbook.

The user-facing [Power Automate Teams Workflow
guide](../../docs/power-automate-teams-workflow.md) contains the from-blank
creation steps, screenshots, callback storage, and smoke test. This runbook
focuses on provider lifecycle, repeat deployment, and attribution verification.

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

## Headless deployment roadmap

The Power Automate portal is not required for repeated deployments after a
from-blank flow has been authored once. The supported ALM path is to store the
flow inside a Power Platform Solution and deploy the Solution with Power
Platform CLI.

The future automation should:

1. add the verified from-blank flow to an unmanaged Solution;
2. replace its concrete Teams connection with a connection reference;
3. represent the target Team and Channel with environment variables;
4. authenticate Power Platform CLI with an approved workload identity;
5. export and unpack the unmanaged Solution as the source artifact;
6. pack and import the Solution into the target environment;
7. bind the target connection reference and environment variables;
8. activate the imported flow;
9. retrieve the HTTP trigger callback URL through the Power Automate management
   API `listCallbackUrl` operation;
10. write the URL directly to the target secret store;
11. run a synthetic rich-card smoke test and assert that the posted card has no
    template attribution.

The automation cannot assume that Microsoft connection consent is portable.
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

Before implementing this roadmap, confirm the current
[Power Platform CLI Solution commands](https://learn.microsoft.com/power-platform/developer/cli/reference/solution),
[cloud-flow code APIs](https://learn.microsoft.com/power-automate/manage-flows-with-code),
and Teams Workflow behavior because callback URL lifecycle and connector
retirement dates can change.

## Footer verification checklist

The gallery-template footer problem must be checked independently of card
rendering:

1. On the flow details page, confirm that **Original template** is absent.
2. Confirm the trigger is **When a Teams webhook request is received**.
3. Confirm the action is **Post card in a chat or channel** with the Adaptive
   Card expression shown above.
4. Retrieve a fresh callback URL after deployment instead of copying one from a
   different environment.
5. Send a synthetic card containing a title, `FactSet`, and `Action.OpenUrl`.
6. Inspect the posted card and confirm that neither the owner attribution nor
   **Get template** appears.

Changing the Adaptive Card JSON, flow name, owner, or callback URL does not
remove attribution from a flow that retains an **Original template**
relationship. Recreating the flow from blank is the verified remedy.
