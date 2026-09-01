# Teams delivery through Azure Logic Apps

The supported Logic App boundary uses a Consumption Logic App with an HTTP
request trigger and an authorized Microsoft Teams managed-connector action.

## Assets

- `main.bicep` deploys the enabled Consumption Logic App and references an
  authorized Teams API connection.
- `workflow-definition.json` owns validation, connector delivery, secure data,
  and explicit HTTP responses.

Deploy from the repository root:

```shell
az deployment group create \
  --name pyhookkit-logic-app \
  --resource-group rg-notify \
  --template-file infra/azure/logic-apps/main.bicep \
  --parameters \
    logicAppName=logic-notify-teams \
    teamsConnectionResourceId="$TEAMS_CONNECTION_ID"
```

OAuth consent remains a separate bootstrap responsibility. The connection may
be shared across workflows in the same subscription and region; its resource ID
is an environment parameter, not committed configuration.

## Request contract

The trigger accepts:

```json
{
  "teamId": "<Teams team ID>",
  "channelId": "<Teams channel ID>",
  "eventId": "<provider-neutral event ID>",
  "card": {
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": []
  }
}
```

`teamId`, `channelId`, and a non-empty Adaptive Card are required. `eventId` is
optional for standalone gallery cards.

The Teams connector action posts `string(triggerBody()?['card'])` to the
requested Team and channel. A successful workflow returns HTTP `201`. Connector
and validation failures must return non-2xx responses so callers cannot mistake
them for successful delivery.

PyHookKit treats any 2xx response as success and returns only the
provider-neutral delivery state and attempt count. It does not expose the
connector response body or Teams message identifiers.

## Local configuration

Store runtime values only in the ignored repository `.env`:

```dotenv
TEAMS_LOGIC_APP_URL="<HTTP trigger callback URL>"
TEAMS_LOGIC_APP_TEAM_ID="<Teams team ID>"
TEAMS_LOGIC_APP_CHANNEL_ID="<Teams channel ID>"
```

The callback URL contains a signature and must be treated as a credential.
Never print it, commit it, or include it in delivery results.

## Run

From `examples/python`:

```shell
uv run python scenarios/deployment_result/teams.py --send-logic-app
```

The rendered card is identical to the Power Automate path. Only the outbound
request adapter differs: it removes the Teams Workflow envelope and adds Logic
App routing fields. This invariant is exercised for every library-backed Teams
example; F00 separately compares its two standard-library request builders.

See the user-facing [Logic App Teams delivery
guide](../../../docs/logic-app-teams-delivery.md) for callback retrieval,
adapter selection, smoke testing, and removal.
