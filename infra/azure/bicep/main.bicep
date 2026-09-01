targetScope = 'resourceGroup'

@description('Location for all resources.')
param location string = resourceGroup().location

@description('AKS cluster name.')
@minLength(3)
@maxLength(63)
param clusterName string

@description('DNS prefix for the AKS API server.')
@minLength(3)
@maxLength(54)
param dnsPrefix string = take(clusterName, 54)

@description('Leave empty to use the region default AKS version.')
param kubernetesVersion string = ''

@description('System node pool size.')
param nodeVmSize string = 'Standard_D2ds_v5'

@description('System node count.')
@minValue(1)
@maxValue(5)
param nodeCount int = 1

@description('Virtual network name.')
param virtualNetworkName string = '${clusterName}-vnet'

@description('AKS subnet name.')
param aksSubnetName string = 'aks-subnet'

@description('Virtual network address space.')
param vnetAddressPrefix string = '10.42.0.0/22'

@description('AKS subnet address space.')
param aksSubnetPrefix string = '10.42.0.0/23'

@description('Kubernetes service CIDR.')
param serviceCidr string = '10.2.0.0/24'

@description('Cluster DNS service IP inside the service CIDR.')
param dnsServiceIp string = '10.2.0.10'

@description('Pod CIDR used by Azure CNI Overlay.')
param podCidr string = '10.244.0.0/16'

@description('Microsoft Entra group object IDs granted cluster admin access.')
param adminGroupObjectIds array = []

@description('Enable Azure RBAC authorization for Kubernetes.')
param enableAzureRbac bool = true

@description('Disable local cluster administrator credentials after Entra access is configured.')
param disableLocalAccounts bool = false

@description('Tags applied to all resources.')
param tags object = {}

var resourceTags = union(tags, {
  workload: 'bookinfo'
  managedBy: 'bicep'
})

var managedClusterProperties = union({
  dnsPrefix: dnsPrefix
  disableLocalAccounts: disableLocalAccounts
  enableRBAC: true
  aadProfile: {
    managed: true
    enableAzureRBAC: enableAzureRbac
    adminGroupObjectIDs: adminGroupObjectIds
  }
  oidcIssuerProfile: {
    enabled: true
  }
  securityProfile: {
    workloadIdentity: {
      enabled: true
    }
  }
  agentPoolProfiles: [
    {
      name: 'system'
      mode: 'System'
      count: nodeCount
      vmSize: nodeVmSize
      osType: 'Linux'
      type: 'VirtualMachineScaleSets'
      maxPods: 30
      vnetSubnetID: aksSubnet.id
    }
  ]
  networkProfile: {
    networkPlugin: 'azure'
    networkPluginMode: 'overlay'
    loadBalancerSku: 'standard'
    outboundType: 'loadBalancer'
    serviceCidr: serviceCidr
    dnsServiceIP: dnsServiceIp
    podCidr: podCidr
  }
}, empty(kubernetesVersion) ? {} : {
  kubernetesVersion: kubernetesVersion
})

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: virtualNetworkName
  location: location
  tags: resourceTags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
  }
}

resource aksSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: virtualNetwork
  name: aksSubnetName
  properties: {
    addressPrefix: aksSubnetPrefix
  }
}

resource cluster 'Microsoft.ContainerService/managedClusters@2024-09-01' = {
  name: clusterName
  location: location
  tags: resourceTags
  sku: {
    name: 'Base'
    tier: 'Free'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: managedClusterProperties
}

output clusterId string = cluster.id
output clusterName string = cluster.name
output nodeResourceGroup string = cluster.properties.nodeResourceGroup
output aksSubnetResourceId string = aksSubnet.id
