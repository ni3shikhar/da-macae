// =============================================================================
// DA-MACAÉ v2 :: App Configuration Module
// =============================================================================
// Azure App Configuration for centralized feature flags and settings.
// Updated for V2 Python/FastAPI multi-service architecture.
// =============================================================================

@description('Project name prefix')
param projectName string

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

// ── Naming ──────────────────────────────────────────────────────────────────

var envSuffix = environment == 'prod' ? '' : '-${environment}'
var appConfigName = '${projectName}-appconfig${envSuffix}'

// ── Configuration per environment ───────────────────────────────────────────

var skuName = environment == 'prod' ? 'standard' : 'free'

// ── App Configuration ───────────────────────────────────────────────────────

resource appConfig 'Microsoft.AppConfiguration/configurationStores@2023-03-01' = {
  name: appConfigName
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  properties: {
    publicNetworkAccess: environment == 'prod' ? 'Disabled' : 'Enabled'
    disableLocalAuth: false
    softDeleteRetentionInDays: environment == 'prod' ? 7 : 1
    enablePurgeProtection: environment == 'prod'
  }
}

// ── Feature Flags ───────────────────────────────────────────────────────────

resource featureAutoApproval 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: '.appconfig.featureflag~2Fda-macae.auto-approval'
  properties: {
    value: '{"id":"da-macae.auto-approval","description":"Enable automatic plan approval for low-risk migrations","enabled":${environment == 'dev'},"conditions":{"client_filters":[]}}'
    contentType: 'application/vnd.microsoft.appconfig.ff+json;charset=utf-8'
  }
}

resource featureParallelExec 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: '.appconfig.featureflag~2Fda-macae.parallel-execution'
  properties: {
    value: '{"id":"da-macae.parallel-execution","description":"Enable parallel agent step execution","enabled":${environment != 'prod' ? true : false},"conditions":{"client_filters":[]}}'
    contentType: 'application/vnd.microsoft.appconfig.ff+json;charset=utf-8'
  }
}

resource featureAdvancedAnalytics 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: '.appconfig.featureflag~2Fda-macae.advanced-analytics'
  properties: {
    value: '{"id":"da-macae.advanced-analytics","description":"Enable advanced migration analytics and reporting","enabled":true,"conditions":{"client_filters":[]}}'
    contentType: 'application/vnd.microsoft.appconfig.ff+json;charset=utf-8'
  }
}

resource featurePrePlanClarification 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: '.appconfig.featureflag~2Fda-macae.pre-plan-clarification'
  properties: {
    value: '{"id":"da-macae.pre-plan-clarification","description":"Enable pre-plan clarification questions before generating migration plan","enabled":true,"conditions":{"client_filters":[]}}'
    contentType: 'application/vnd.microsoft.appconfig.ff+json;charset=utf-8'
  }
}

// ── Application Settings ────────────────────────────────────────────────────

resource settingMigrationMaxRetries 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: 'da-macae:migration:max-retries$${environment}'
  properties: {
    value: environment == 'prod' ? '5' : '3'
  }
}

resource settingMigrationTimeout 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: 'da-macae:migration:timeout-minutes$${environment}'
  properties: {
    value: environment == 'prod' ? '60' : '30'
  }
}

resource settingDatabaseBackend 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: 'da-macae:database:backend$${environment}'
  properties: {
    value: 'cosmosdb'
  }
}

resource settingMcpServerUrl 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: 'da-macae:mcp-server:url$${environment}'
  properties: {
    value: environment == 'prod' ? 'http://mcp-server:8001' : 'http://mcp-server:8001'
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output id string = appConfig.id
output name string = appConfig.name
output endpoint string = appConfig.properties.endpoint
