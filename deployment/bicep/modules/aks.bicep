// =============================================================================
// DA-MACAÉ :: AKS Cluster Module
// =============================================================================
// Managed Kubernetes cluster with Workload Identity, CSI driver, monitoring
// =============================================================================

@description('Project name prefix')
param projectName string

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Azure region')
param location string

@description('Admin principal ID for cluster admin')
param adminObjectId string

@description('ACR resource ID for pull permissions')
param acrId string

@description('Log Analytics workspace ID')
param logAnalyticsWorkspaceId string

@description('Resource tags')
param tags object

// ── Naming ──────────────────────────────────────────────────────────────────

var envSuffix = environment == 'prod' ? '' : '-${environment}'
var clusterName = '${projectName}-aks${envSuffix}'
var nodeResourceGroup = '${projectName}-aks-nodes${envSuffix}'

// ── Configuration per environment ───────────────────────────────────────────

var nodeConfig = {
  dev: {
    vmSize: 'Standard_D2s_v5'
    minCount: 1
    maxCount: 3
    nodeCount: 1
    osDiskSizeGB: 64
    maxPods: 30
  }
  staging: {
    vmSize: 'Standard_D4s_v5'
    minCount: 2
    maxCount: 5
    nodeCount: 2
    osDiskSizeGB: 128
    maxPods: 50
  }
  prod: {
    vmSize: 'Standard_D8s_v5'
    minCount: 3
    maxCount: 10
    nodeCount: 3
    osDiskSizeGB: 128
    maxPods: 50
  }
}

var kubernetesVersion = '1.32'

// ── AKS Cluster ─────────────────────────────────────────────────────────────

resource aks 'Microsoft.ContainerService/managedClusters@2024-06-02-preview' = {
  name: clusterName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Base'
    tier: environment == 'prod' ? 'Standard' : 'Free'
  }
  properties: {
    kubernetesVersion: kubernetesVersion
    dnsPrefix: '${projectName}-${environment}'
    nodeResourceGroup: nodeResourceGroup

    agentPoolProfiles: [
      {
        name: 'system'
        count: nodeConfig[environment].nodeCount
        vmSize: nodeConfig[environment].vmSize
        osDiskSizeGB: nodeConfig[environment].osDiskSizeGB
        osDiskType: 'Managed'
        osType: 'Linux'
        osSKU: 'AzureLinux'
        mode: 'System'
        enableAutoScaling: true
        minCount: nodeConfig[environment].minCount
        maxCount: nodeConfig[environment].maxCount
        maxPods: nodeConfig[environment].maxPods
        availabilityZones: environment == 'prod' ? ['1', '2', '3'] : null
        upgradeSettings: {
          maxSurge: '33%'
        }
        nodeTaints: []
        nodeLabels: {
          'workload': 'da-macae'
          'environment': environment
        }
      }
    ]

    networkProfile: {
      networkPlugin: 'azure'
      networkPolicy: 'calico'
      serviceCidr: '10.0.0.0/16'
      dnsServiceIP: '10.0.0.10'
      loadBalancerSku: 'standard'
      outboundType: 'loadBalancer'
    }

    // Workload Identity
    oidcIssuerProfile: {
      enabled: true
    }
    securityProfile: {
      workloadIdentity: {
        enabled: true
      }
      defender: {
        securityMonitoring: {
          enabled: environment == 'prod'
        }
      }
      imageCleaner: {
        enabled: true
        intervalHours: 24
      }
    }

    // RBAC
    aadProfile: {
      managed: true
      enableAzureRBAC: true
      adminGroupObjectIDs: [adminObjectId]
    }
    enableRBAC: true

    // Add-ons
    addonProfiles: {
      omsagent: {
        enabled: true
        config: {
          logAnalyticsWorkspaceResourceID: logAnalyticsWorkspaceId
        }
      }
      azureKeyvaultSecretsProvider: {
        enabled: true
        config: {
          enableSecretRotation: 'true'
          rotationPollInterval: '120s'
        }
      }
      ingressApplicationGateway: {
        enabled: false
      }
    }

    // Maintenance
    autoUpgradeProfile: {
      upgradeChannel: environment == 'prod' ? 'stable' : 'rapid'
    }

    // Monitoring
    azureMonitorProfile: {
      metrics: {
        enabled: true
      }
    }
  }
}

// ── ACR Pull Role Assignment ────────────────────────────────────────────────

// AcrPull role: 7f951dda-4ed3-4680-a7ca-43fe172d538d
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, acrId, 'AcrPull')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: aks.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output clusterName string = aks.name
output clusterId string = aks.id
output clusterFqdn string = aks.properties.fqdn
output kubeletIdentityObjectId string = aks.properties.identityProfile.kubeletidentity.objectId
output oidcIssuerUrl string = aks.properties.oidcIssuerProfile.issuerURL
