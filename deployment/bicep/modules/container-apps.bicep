// =============================================================================
// DA-MACAE :: Container Apps Module
// =============================================================================
// Creates Container Apps Environment + 3 apps for AZD deploy target.
// Apps start with placeholder images; azd deploy updates them.
// =============================================================================

@description('Project name prefix')
param projectName string

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Azure region')
param location string

@description('ACR login server (empty string for first deploy)')
param acrLoginServer string

@description('ACR resource name — used to grant AcrPull to Container App identities')
param acrName string

@description('Log Analytics workspace name')
param logAnalyticsWorkspaceName string

// Always use public placeholder image for initial provisioning.
// azd deploy will update containers with real ACR images afterward.
var placeholderImage = 'mcr.microsoft.com/k8se/quickstart:latest'

// AcrPull built-in role definition ID (constant across all subscriptions)
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

// Reference existing ACR so we can scope role assignments to it
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: acrName
}

@description('Resource tags')
param tags object

// ── Naming ──────────────────────────────────────────────────────────────────

var envSuffix = environment == 'prod' ? '' : '-${environment}'
var containerEnvName = '${projectName}-env${envSuffix}'

// ── Container Apps Environment ──────────────────────────────────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsWorkspaceName
}

resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    zoneRedundant: environment == 'prod'
  }
}

// ── Backend Container App ───────────────────────────────────────────────────

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${projectName}-backend${envSuffix}'
  location: location
  tags: union(tags, { 'azd-service-name': 'backend' })
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
      }
      registries: acrLoginServer != '' ? [{ server: acrLoginServer, identity: 'system' }] : []
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: placeholderImage
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: environment == 'prod' ? 10 : 3
      }
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ── Frontend Container App ──────────────────────────────────────────────────

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${projectName}-frontend${envSuffix}'
  location: location
  tags: union(tags, { 'azd-service-name': 'frontend' })
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
      }
      registries: acrLoginServer != '' ? [{ server: acrLoginServer, identity: 'system' }] : []
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: placeholderImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: environment == 'prod' ? 5 : 2
      }
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ── MCP Server Container App ────────────────────────────────────────────────

resource mcpApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${projectName}-mcp${envSuffix}'
  location: location
  tags: union(tags, { 'azd-service-name': 'mcp-server' })
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8001
        transport: 'http'
      }
      registries: acrLoginServer != '' ? [{ server: acrLoginServer, identity: 'system' }] : []
    }
    template: {
      containers: [
        {
          name: 'mcp-server'
          image: placeholderImage
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: environment == 'prod' ? 8 : 3
      }
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ── AcrPull role assignments (system-assigned identity → ACR) ───────────────
// Allows each Container App to pull images from ACR without admin credentials.

resource backendAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (acrLoginServer != '') {
  name: guid(acr.id, backendApp.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: backendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource frontendAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (acrLoginServer != '') {
  name: guid(acr.id, frontendApp.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: frontendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource mcpAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (acrLoginServer != '') {
  name: guid(acr.id, mcpApp.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: mcpApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output environmentId string = containerEnv.id
output backendFqdn string = backendApp.properties.configuration.ingress.fqdn
output frontendFqdn string = frontendApp.properties.configuration.ingress.fqdn
output mcpFqdn string = mcpApp.properties.configuration.ingress.fqdn
