targetScope = 'resourceGroup'

@description('Logic App name.')
@minLength(1)
param logicAppName string

@description('Azure region for the Logic App and managed Teams API.')
param location string = resourceGroup().location

@description('Resource ID of an authorized Microsoft.Web/connections Teams connection.')
@minLength(1)
param teamsConnectionResourceId string

@description('Tags applied to the Logic App.')
param tags object = {}

var teamsConnectionName = last(split(teamsConnectionResourceId, '/'))
var teamsManagedApiId = subscriptionResourceId(
  'Microsoft.Web/locations/managedApis',
  location,
  'teams'
)

resource logicApp 'Microsoft.Logic/workflows@2019-05-01' = {
  name: logicAppName
  location: location
  tags: union(tags, {
    workload: 'pyhookkit'
    capability: 'teams-delivery'
    managedBy: 'bicep'
  })
  properties: {
    state: 'Enabled'
    definition: loadJsonContent('workflow-definition.json')
    parameters: {
      '$connections': {
        value: {
          teams: {
            id: teamsManagedApiId
            connectionId: teamsConnectionResourceId
            connectionName: teamsConnectionName
          }
        }
      }
    }
  }
}

output logicAppId string = logicApp.id
output logicAppName string = logicApp.name
output triggerName string = 'When_a_HTTP_request_is_received'
