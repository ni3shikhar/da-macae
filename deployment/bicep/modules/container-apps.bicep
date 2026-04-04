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

@description('Log Analytics workspace name')
param logAnalyticsWorkspaceName string

// Use mcr placeholder if no ACR images exist yet (first deploy)
var backendImage = acrLoginServer != '' ? '${acrLoginServer}/agentra-backend:latest' : 'mcr.microsoft.com/k8se/quickstart:latest'
var frontendImage = acrLoginServer != '' ? '${acrLoginServer}/agentra-frontend:latest' : 'mcr.microsoft.com/k8se/quickstart:latest'
var mcpImage = acrLoginServer != '' ? '${acrLoginServer}/agentra-mcp:latest' : 'mcr.microsoft.com/k8se/quickstart:latest'

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
      registries: acrLoginServer != '' ? [
        {
          server: acrLoginServer
          identity: 'system'
        }
      ] : []
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
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
      registries: acrLoginServer != '' ? [
        {
          server: acrLoginServer
          identity: 'system'
        }
      ] : []
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
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
      registries: acrLoginServer != '' ? [
        {
          server: acrLoginServer
          identity: 'system'
        }
      ] : []
    }
    template: {
      containers: [
        {
          name: 'mcp-server'
          image: mcpImage
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

// ── Outputs ─────────────────────────────────────────────────────────────────

output environmentId string = containerEnv.id
output backendFqdn string = backendApp.properties.configuration.ingress.fqdn
output frontendFqdn string = frontendApp.properties.configuration.ingress.fqdn
output mcpFqdn string = mcpApp.properties.configuration.ingress.fqdn
