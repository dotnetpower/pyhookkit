# TeamsNotifyApp bootstrap

[한국어](teams-notify-app-bootstrap.ko.md)

> [!IMPORTANT]
> `TeamsNotifyApp` is not required for the first Teams Webhook notification. For
> a small number of Teams, have a Team owner add the posting identity manually
> and use the [10-minute Teams Webhook quickstart](teams-webhook-quickstart.md).

`TeamsNotifyApp` is an optional, visible single-tenant Entra application for
automating the repeated addition of the Power Automate posting identity to many
standard Teams. When a destination is registered in the central router, it
checks the backing Microsoft 365 Group and adds the posting identity through
Microsoft Graph when absent.

The app does not post Teams messages, replace the Power Automate Microsoft Teams
connection or MFA, or grant channel-specific membership to private and shared
channels.

When selected, it replaces saved Azure CLI delegated access tokens. The router obtains a
short-lived app-only Microsoft Graph token whenever it performs membership
registration.

`TeamsNotifyApp` is not an Azure resource created in an Azure subscription. It
is an app registration and Service Principal in the same Microsoft Entra
tenant as the Microsoft 365 tenant that owns the destination Team and channel.
A "Microsoft 365 user" is a user from that same Entra directory with Teams
licensing, not a user from a separate directory. Azure CLI signs in to this
Entra tenant; no Azure subscription or Azure RBAC role is required.

## Identity boundaries

Do not combine these identities merely to simplify bootstrap:

| Identity | Responsibility | Minimum access |
|---|---|---|
| Bootstrap app creator | Create `TeamsNotifyApp`, its Service Principal, and its client credential | No directory role when tenant policy permits user app registration; otherwise **Application Developer** |
| Consent approver | Grant `GroupMember.ReadWrite.All` as a Microsoft Graph application permission | **Privileged Role Administrator**; activate temporarily through PIM where available |
| Flow author | Create the Power Automate Flow and bind its Teams connection | Power Platform **Environment Maker** in the selected environment |
| Teams connection user | Authorize the Teams connector and send cards | Licensed Microsoft 365/Teams and Power Automate user; no Entra administrator role |
| TeamsNotifyApp runtime | Add the connection user to explicitly registered Team backing groups | Microsoft Graph application permission `GroupMember.ReadWrite.All` |
| Notification producer | Submit canonical notifications | Producer-specific router bearer token only |

When tenant policy already allows ordinary users to register applications, the
bootstrap app creator becomes the owner of the new app and can manage its
credential. A separate operator needs **Cloud Application Administrator** to
manage an app they do not own.

Microsoft Graph application roles require tenant-wide admin consent.
**Privileged Role Administrator** is the least privileged built-in role that
can grant consent for Microsoft Graph application permissions. Global
Administrator is broader and is not the recommended routine bootstrap role.

The current one-command bootstrap expects the operator to be allowed to create
the app and to have an active Privileged Role Administrator role. An
organization can separate those duties, but the consent approver must complete
consent before the command can validate the app-only token.

Official references:

- [least-privileged roles by task](https://learn.microsoft.com/entra/identity/role-based-access-control/delegate-by-task);
- [grant tenant-wide admin consent](https://learn.microsoft.com/entra/identity/enterprise-apps/grant-admin-consent);
- [application and Service Principal objects](https://learn.microsoft.com/entra/identity-platform/app-objects-and-service-principals);
- [add members to a Microsoft 365 Group](https://learn.microsoft.com/graph/api/group-post-members?view=graph-rest-1.0);
- [Microsoft Graph permissions reference](https://learn.microsoft.com/graph/permissions-reference).

## Manual prerequisites

1. Create the Power Automate Flow from blank.
2. Use **When a Teams webhook request is received**.
3. Configure **Post card in a chat or channel**:
   - **Post as**: `Flow bot`;
   - **Post in**: `Channel`;
   - **Team**: `triggerBody()?['teamId']`;
   - **Channel**: `triggerBody()?['channelId']`;
   - **Adaptive Card**:
     `first(triggerBody()?['attachments'])?['content']`.
4. Create the Microsoft Teams connection by signing in as the dedicated
   `svc-teams-notification` account.
5. Store the complete generated callback in the ignored repository `.env`:

   ```dotenv
   TEAMS_WORKFLOW_URL="<complete signed callback URL>"
   ```

The Power Automate connection authorization remains interactive because it can
require MFA and Conditional Access. App bootstrap cannot convert a user Teams
connection into application authentication.

## Bootstrap

Find the `tenantId=<GUID>` value in the Teams channel link query string. This is
the target Entra tenant ID. Sign in to that tenant with the bootstrap/consent
identity, then verify the current Azure CLI account:

```shell
az login \
  --tenant "<channel tenant GUID>" \
  --use-device-code \
  --allow-no-subscriptions

az account show \
  --query "{signedInUser:user.name, tenantId:tenantId}" \
  --output table
```

Confirm that `signedInUser` is the intended bootstrap administrator identity
and that the reported `tenantId` exactly matches the channel link's `tenantId`.
If either value differs, do not run the bootstrap; sign in again with the
correct identity and `--tenant` value.

> [!IMPORTANT]
> `az account show` verifies only the current Azure CLI user and tenant. It does
> not verify app-registration permission or an active **Privileged Role
> Administrator** role; verify those separately in Entra or PIM.

From `examples/python`, run:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  bootstrap-teams-app \
  --channel-link "<initial Teams channel link>" \
  --connection-user "svc-teams-notification@example.com" \
  --route release-notifications
```

The command automatically:

1. derives the tenant, Team, channel, and display name from the link;
2. verifies that Azure CLI can acquire a Graph token for that tenant;
3. creates or uniquely reuses `TeamsNotifyApp`;
4. creates or reuses its tenant Service Principal;
5. resolves the current Microsoft Graph app-role identifier rather than
   hard-coding a permission GUID;
6. configures `GroupMember.ReadWrite.All`;
7. creates and verifies the Service Principal app-role assignment;
8. resolves the Teams connection user to an Entra object ID;
9. creates a one-year credential when a reusable credential is unavailable;
10. validates a client-credentials token's tenant, client ID, and `roles`;
11. atomically writes the generated values to `.env` with mode `0600`;
12. idempotently adds the connection user to the Team's backing Microsoft 365
    Group;
13. stores the route in SQLite.

If token validation or `.env` persistence fails after credential creation, the
new credential is deleted automatically. The secret is never printed.

Generated configuration:

```dotenv
TEAMS_NOTIFY_TENANT_ID="<tenant GUID>"
TEAMS_NOTIFY_CLIENT_ID="<TeamsNotifyApp client GUID>"
TEAMS_NOTIFY_CLIENT_SECRET="<generated secret>"
TEAMS_CONNECTION_USER_ID="<connection user object GUID>"
```

The tenant ID comes from the channel link. The service user object ID is
resolved once during bootstrap, so TeamsNotifyApp does not need a directory-wide
user-read permission at runtime.

## Portal verification

In Microsoft Entra admin center:

1. Open **App registrations** and select `TeamsNotifyApp`.
2. Under **API permissions**, confirm Microsoft Graph
   `GroupMember.ReadWrite.All` is an **Application** permission.
3. Confirm the status is **Granted for \<tenant\>**.
4. Open **Enterprise applications** and select `TeamsNotifyApp`.
5. Under **Permissions**, confirm the same application permission.
6. Under **Owners**, retain at least two named operational owners.
7. Under **Certificates & secrets**, confirm only expected PyHookKit
   credentials remain.

The Teams connection user is separate. In Power Automate, confirm the Teams
action shows that service account under **Connected to**.

## Add another channel

The repository `.env` is loaded automatically. No Graph access token is copied
or exported:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id teams-example-channel \
  --route release-notifications \
  --provider teams-workflow \
  --endpoint-env TEAMS_WORKFLOW_URL \
  --channel-link "<Teams channel link>" \
  --ensure-team-membership
```

Registration rejects cross-tenant links, obtains a fresh app-only token, checks
existing membership, and adds only a normal group member when absent. Repeating
the command is safe.

Standard channels follow Team membership. Private and shared channels can
require explicit channel membership. Flow bot delivery to private channels is
not supported by this setup.

## Diagnose

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  doctor
```

Healthy output confirms:

- Workflow URL validation;
- client-credentials token acquisition;
- matching token tenant and client ID;
- required Graph application role;
- service-account membership for every enabled Teams destination;
- SQLite mode `0600`.

`doctor` does not send a notification and never prints credentials.

## Rotate the client secret

Re-run bootstrap with:

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  bootstrap-teams-app \
  --channel-link "<existing Teams channel link>" \
  --connection-user "svc-teams-notification@example.com" \
  --target-id teams-example-channel \
  --rotate-secret
```

After bootstrap and `doctor` succeed, delete the older credential in Entra.
Retain at least one working credential until the new app-only token has been
verified.

## Recovery and removal

- If app-token acquisition returns `401`, rotate the client credential.
- If the token lacks `roles`, verify the Service Principal app-role assignment
  and tenant-wide admin consent.
- If membership returns `403`, verify `GroupMember.ReadWrite.All` consent.
- If Teams posting fails after membership succeeds, reauthorize the Power
  Automate Teams connection and confirm it is connected as the service account.
- Before deleting TeamsNotifyApp, disable membership-enabled channel
  registration and verify no bootstrap or recovery process depends on it.
- Delete the App Registration to remove its Service Principal and credentials,
  then remove the four generated app and connection-user values from `.env`.
