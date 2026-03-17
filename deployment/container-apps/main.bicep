// =============================================================================
// DA-MACAÉ v2 :: Azure Container Apps Deployment
// =============================================================================
// Deploys three container apps for the V2 architecture:
//   1. backend   — Python/FastAPI API server (port 8000)
//   2. frontend  — React/Vite static site served by Nginx (port 80)
//   3. mcp-server — MCP tool server for data source operations (port 8001)
//
// V2 does NOT use DAPR — uses direct Cosmos DB SDK + WebSocket for real-time.
// =============================================================================

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Container image tag')
param imageTag string = 'latest'

@description('Container Registry login server')
param containerRegistryServer string

@description('Container Registry username')
@secure()
param containerRegistryUsername string

@description('Container Registry password')
@secure()
param containerRegistryPassword string

@description('Azure OpenAI endpoint')
@secure()
param azureOpenAiEndpoint string

@description('Azure OpenAI API key')
@secure()
param azureOpenAiApiKey string

@description('Azure Cosmos DB endpoint')
@secure()
param cosmosDbEndpoint string

@description('Azure Cosmos DB master key')
@secure()
param cosmosDbKey string

@description('Azure Storage connection string')
@secure()
param storageConnectionString string

@description('Application Insights connection string')
@secure()
param appInsightsConnectionString string

@description('Azure Key Vault name')
param keyVaultName string

@description('AI Foundry project connection string (optional)')
@secure()
param aiFoundryConnectionString string = ''

// ── Naming convention ───────────────────────────────────────────────────────
var prefix = 'damacae'
var envSuffix = environment == 'prod' ? '' : '-${environment}'
var backendAppName = '${prefix}-backend${envSuffix}'
var frontendAppName = '${prefix}-frontend${envSuffix}'
var mcpServerAppName = '${prefix}-mcp${envSuffix}'
var containerEnvName = '${prefix}-env${envSuffix}'

// ── Environment sizing ──────────────────────────────────────────────────────
var backendConfig = {
  dev: { cpu: '1.0', memory: '2Gi', minReplicas: 1, maxReplicas: 3 }
  staging: { cpu: '1.5', memory: '3Gi', minReplicas: 1, maxReplicas: 5 }
  prod: { cpu: '2.0', memory: '4Gi', minReplicas: 2, maxReplicas: 10 }
}

var frontendConfig = {
  dev: { cpu: '0.25', memory: '0.5Gi', minReplicas: 1, maxReplicas: 2 }
  staging: { cpu: '0.5', memory: '1Gi', minReplicas: 1, maxReplicas: 3 }
  prod: { cpu: '0.5', memory: '1Gi', minReplicas: 2, maxReplicas: 5 }
}

var mcpConfig = {
  dev: { cpu: '1.0', memory: '2Gi', minReplicas: 1, maxReplicas: 3 }
  staging: { cpu: '1.5', memory: '3Gi', minReplicas: 1, maxReplicas: 5 }
  prod: { cpu: '2.0', memory: '4Gi', minReplicas: 2, maxReplicas: 8 }
}

// ── Log Analytics Workspace ─────────────────────────────────────────────────
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs${envSuffix}'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: environment == 'prod' ? 90 : 30
  }
}

// ── Container Apps Environment ──────────────────────────────────────────────
resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: environment == 'prod'
  }
}

// ── Shared secrets & registry config ────────────────────────────────────────
var sharedSecrets = [
  { name: 'registry-password', value: containerRegistryPassword }
  { name: 'cosmos-endpoint', value: cosmosDbEndpoint }
  { name: 'cosmos-key', value: cosmosDbKey }
  { name: 'openai-endpoint', value: azureOpenAiEndpoint }
  { name: 'openai-api-key', value: azureOpenAiApiKey }
  { name: 'storage-connection', value: storageConnectionString }
  { name: 'appinsights-connection', value: appInsightsConnectionString }
  { name: 'ai-foundry-connection', value: aiFoundryConnectionString }
]

var registryConfig = [
  {
    server: containerRegistryServer
    username: containerRegistryUsername
    passwordSecretRef: 'registry-password'
  }
]

// ═══════════════════════════════════════════════════════════════════════════
// Container App: Backend (Python / FastAPI)
// ═══════════════════════════════════════════════════════════════════════════
resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: backendAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Multiple'
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
        traffic: [
          { latestRevision: true, weight: 100 }
        ]
      }
      secrets: sharedSecrets
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${containerRegistryServer}/da-macae-backend:${imageTag}'
          resources: {
            cpu: json(backendConfig[environment].cpu)
            memory: backendConfig[environment].memory
          }
          env: [
            { name: 'AZURE_OPENAI_ENDPOINT', secretRef: 'openai-endpoint' }
            { name: 'AZURE_OPENAI_API_KEY', secretRef: 'openai-api-key' }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: 'gpt-4o' }
            { name: 'AZURE_OPENAI_API_VERSION', value: '2024-12-01-preview' }
            { name: 'COSMOS_ENDPOINT', secretRef: 'cosmos-endpoint' }
            { name: 'COSMOS_KEY', secretRef: 'cosmos-key' }
            { name: 'COSMOS_DATABASE', value: 'damacae' }
            { name: 'COSMOS_CONTAINER', value: 'sessions' }
            { name: 'DATABASE_BACKEND', value: 'cosmosdb' }
            { name: 'MCP_SERVER_URL', value: 'http://${mcpServerAppName}:8001' }
            { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-connection' }
            { name: 'AI_FOUNDRY_PROJECT_CONNECTION_STRING', secretRef: 'ai-foundry-connection' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'appinsights-connection' }
            { name: 'KEY_VAULT_NAME', value: keyVaultName }
            { name: 'LOG_LEVEL', value: environment == 'prod' ? 'WARNING' : 'INFO' }
            { name: 'TEAM_DATA_DIR', value: '/app/data/agent_teams' }
          ]
          probes: [
            {
              type: 'startup'
              httpGet: { path: '/api/v1/health', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 5
              failureThreshold: 12
            }
            {
              type: 'liveness'
              httpGet: { path: '/api/v1/health', port: 8000 }
              periodSeconds: 15
              failureThreshold: 3
            }
            {
              type: 'readiness'
              httpGet: { path: '/api/v1/health', port: 8000 }
              periodSeconds: 10
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: backendConfig[environment].minReplicas
        maxReplicas: backendConfig[environment].maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: { concurrentRequests: '20' }
            }
          }
        ]
      }
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Container App: Frontend (React / Nginx)
// ═══════════════════════════════════════════════════════════════════════════
resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: frontendAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Multiple'
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
        corsPolicy: {
          allowedOrigins: environment == 'prod'
            ? ['https://da-macae.example.com']
            : ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          maxAge: 3600
        }
        traffic: [
          { latestRevision: true, weight: 100 }
        ]
      }
      secrets: [
        { name: 'registry-password', value: containerRegistryPassword }
      ]
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${containerRegistryServer}/da-macae-frontend:${imageTag}'
          resources: {
            cpu: json(frontendConfig[environment].cpu)
            memory: frontendConfig[environment].memory
          }
          probes: [
            {
              type: 'startup'
              httpGet: { path: '/', port: 80 }
              initialDelaySeconds: 5
              periodSeconds: 5
              failureThreshold: 6
            }
            {
              type: 'liveness'
              httpGet: { path: '/', port: 80 }
              periodSeconds: 30
              failureThreshold: 3
            }
            {
              type: 'readiness'
              httpGet: { path: '/', port: 80 }
              periodSeconds: 10
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: frontendConfig[environment].minReplicas
        maxReplicas: frontendConfig[environment].maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: { concurrentRequests: '50' }
            }
          }
        ]
      }
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Container App: MCP Server (Python / FastMCP)
// ═══════════════════════════════════════════════════════════════════════════
resource mcpServerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: mcpServerAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Multiple'
      ingress: {
        external: false
        targetPort: 8001
        transport: 'http'
        traffic: [
          { latestRevision: true, weight: 100 }
        ]
      }
      secrets: sharedSecrets
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'mcp-server'
          image: '${containerRegistryServer}/da-macae-mcp:${imageTag}'
          resources: {
            cpu: json(mcpConfig[environment].cpu)
            memory: mcpConfig[environment].memory
          }
          env: [
            { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-connection' }
            { name: 'COSMOS_ENDPOINT', secretRef: 'cosmos-endpoint' }
            { name: 'COSMOS_KEY', secretRef: 'cosmos-key' }
            { name: 'LOG_LEVEL', value: environment == 'prod' ? 'WARNING' : 'INFO' }
            // External data source connections are injected per-deployment
          ]
          probes: [
            {
              type: 'startup'
              httpGet: { path: '/health', port: 8001 }
              initialDelaySeconds: 10
              periodSeconds: 5
              failureThreshold: 12
            }
            {
              type: 'liveness'
              httpGet: { path: '/health', port: 8001 }
              periodSeconds: 15
              failureThreshold: 3
            }
            {
              type: 'readiness'
              httpGet: { path: '/health', port: 8001 }
              periodSeconds: 10
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: mcpConfig[environment].minReplicas
        maxReplicas: mcpConfig[environment].maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: { concurrentRequests: '15' }
            }
          }
        ]
      }
    }
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output backendAppId string = backendApp.id
output backendIdentityPrincipalId string = backendApp.identity.principalId
output mcpServerAppId string = mcpServerApp.id
output mcpServerIdentityPrincipalId string = mcpServerApp.identity.principalId
output containerEnvId string = containerEnv.id
