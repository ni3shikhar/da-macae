// =============================================================================
// DA-MACAÉ v2 :: Main Infrastructure Orchestrator
// =============================================================================
// Composes all Azure resource modules for the DA-MACAÉ platform.
// V2: Python/FastAPI backend, React frontend, FastMCP server.
// Deployed at subscription scope to manage resource groups.
// =============================================================================

targetScope = 'subscription'

// ── Parameters ──────────────────────────────────────────────────────────────

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Primary Azure region')
param location string = 'eastus2'

@description('Project name used as naming prefix')
param projectName string = 'damacae'

@description('Azure AD admin object ID for Key Vault and AKS')
param adminObjectId string

@description('Azure OpenAI model deployment name')
param openAiModelDeployment string = 'gpt-4o'

@description('Tags applied to all resources')
param tags object = {
  project: 'da-macae'
  environment: environment
  managedBy: 'bicep'
}

// ── Naming Convention ───────────────────────────────────────────────────────

// Unique suffix derived from subscription ID to avoid soft-delete name conflicts
var uniqueSuffix = substring(uniqueString(subscription().subscriptionId, projectName), 0, 5)
var envSuffix = environment == 'prod' ? '' : '-${environment}'
var rgName = '${projectName}-rg${envSuffix}'

// ── Resource Group ──────────────────────────────────────────────────────────

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: tags
}

// ── Log Analytics & Application Insights ────────────────────────────────────

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-${environment}'
  scope: rg
  params: {
    projectName: projectName
    environment: environment
    location: location
    tags: tags
  }
}

// ── Key Vault ───────────────────────────────────────────────────────────────

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault-${environment}'
  scope: rg
  params: {
    projectName: projectName
    environment: environment
    location: location
    adminObjectId: adminObjectId
    uniqueSuffix: uniqueSuffix
    tags: tags
  }
}

// ── Cosmos DB ───────────────────────────────────────────────────────────────

module cosmosDb 'modules/cosmosdb.bicep' = {
  name: 'cosmosdb-${environment}'
  scope: rg
  params: {
    projectName: projectName
    environment: environment
    location: location
    keyVaultName: keyVault.outputs.name
    tags: tags
  }
}

// ── Service Bus ─────────────────────────────────────────────────────────────

module serviceBus 'modules/servicebus.bicep' = {
  name: 'servicebus-${environment}'
  scope: rg
  params: {
    projectName: projectName
    environment: environment
    location: location
    keyVaultName: keyVault.outputs.name
    tags: tags
  }
}

// ── Storage Account ─────────────────────────────────────────────────────────

module storage 'modules/storage.bicep' = {
  name: 'storage-${environment}'
  scope: rg
  params: {
    projectName: projectName
    environment: environment
    location: location
    keyVaultName: keyVault.outputs.name
    tags: tags
  }
}

// ── Azure OpenAI ────────────────────────────────────────────────────────────

module openAi 'modules/openai.bicep' = {
  name: 'openai-${environment}'
  scope: rg
  params: {
    projectName: projectName
    environment: environment
    location: location
    modelDeployment: openAiModelDeployment
    keyVaultName: keyVault.outputs.name
    uniqueSuffix: uniqueSuffix
    tags: tags
  }
}

// ── Container Registry ──────────────────────────────────────────────────────

module acr 'modules/acr.bicep' = {
  name: 'acr-${environment}'
  scope: rg
  params: {
    projectName: projectName
    environment: environment
    location: location
    uniqueSuffix: uniqueSuffix
    tags: tags
  }
}

// ── App Configuration ───────────────────────────────────────────────────────

module appConfig 'modules/appconfig.bicep' = {
  name: 'appconfig-${environment}'
  scope: rg
  params: {
    projectName: projectName
    environment: environment
    location: location
    tags: tags
  }
}

// ── Azure Data Factory ──────────────────────────────────────────────────────

module adf 'modules/adf.bicep' = {
  name: 'adf-${environment}'
  scope: rg
  params: {
    projectName: projectName
    environment: environment
    location: location
    keyVaultName: keyVault.outputs.name
    tags: tags
  }
}

// ── AKS Cluster ─────────────────────────────────────────────────────────────

module aks 'modules/aks.bicep' = {
  name: 'aks-${environment}'
  scope: rg
  params: {
    projectName: projectName
    environment: environment
    location: location
    adminObjectId: adminObjectId
    acrId: acr.outputs.id
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    tags: tags
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output resourceGroupName string = rg.name
output aksClusterName string = aks.outputs.clusterName
output acrLoginServer string = acr.outputs.loginServer
output keyVaultName string = keyVault.outputs.name
output cosmosDbEndpoint string = cosmosDb.outputs.endpoint
output serviceBusNamespace string = serviceBus.outputs.namespaceName
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
output openAiEndpoint string = openAi.outputs.endpoint
output storageBlobEndpoint string = storage.outputs.primaryBlobEndpoint
output storageDfsEndpoint string = storage.outputs.primaryDfsEndpoint
output storageAccountName string = storage.outputs.name
output dataFactoryName string = adf.outputs.name
