// =============================================================================
// DA-MACAÉ v2 :: Storage Account Module
// =============================================================================
// ADLS Gen2-enabled storage for migration artifacts, file ingestion,
// SQL scripts, reports, and data staging across all data source types.
// =============================================================================

@description('Project name prefix')
param projectName string

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Azure region')
param location string

@description('Key Vault name for storing connection secrets')
param keyVaultName string

@description('Resource tags')
param tags object

// ── Naming ──────────────────────────────────────────────────────────────────

// Storage account names must be 3-24 lowercase alphanumeric
var envSuffix = environment == 'prod' ? '' : environment
var storageAccountName = '${projectName}storage${envSuffix}'

// ── Configuration per environment ───────────────────────────────────────────

var skuName = environment == 'prod' ? 'Standard_ZRS' : 'Standard_LRS'
var accessTier = 'Hot'

// ── Storage Account (ADLS Gen2 enabled) ─────────────────────────────────────

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  kind: 'StorageV2'
  properties: {
    accessTier: accessTier
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    publicNetworkAccess: environment == 'prod' ? 'Disabled' : 'Enabled'
    networkAcls: environment == 'prod' ? {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
    } : {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
    encryption: {
      services: {
        blob: { enabled: true, keyType: 'Account' }
        file: { enabled: true, keyType: 'Account' }
        queue: { enabled: true, keyType: 'Account' }
        table: { enabled: true, keyType: 'Account' }
      }
      keySource: 'Microsoft.Storage'
    }
    // ADLS Gen2: hierarchical namespace required for Data Lake tools
    isHnsEnabled: true
  }
}

// ── Blob Service ────────────────────────────────────────────────────────────

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: environment == 'prod' ? 30 : 7
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: environment == 'prod' ? 30 : 7
    }
    isVersioningEnabled: environment == 'prod'
    changeFeed: {
      enabled: environment == 'prod'
    }
  }
}

// ── Container: migration-artifacts ──────────────────────────────────────────

resource artifactsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'migration-artifacts'
  properties: {
    publicAccess: 'None'
  }
}

// ── Container: sql-scripts ──────────────────────────────────────────────────

resource sqlScriptsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'sql-scripts'
  properties: {
    publicAccess: 'None'
  }
}

// ── Container: reports ──────────────────────────────────────────────────────

resource reportsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'reports'
  properties: {
    publicAccess: 'None'
  }
}

// ── Container: data-staging (file ingestion for CSV/Parquet/JSON) ───────────

resource dataStagingContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'data-staging'
  properties: {
    publicAccess: 'None'
  }
}

// ── Container: data-lake (ADLS Gen2 hierarchical storage) ──────────────────

resource dataLakeContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'data-lake'
  properties: {
    publicAccess: 'None'
  }
}

// ── Store secrets in Key Vault ──────────────────────────────────────────────

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource storageConnectionSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'azure-storage-connection-string'
  properties: {
    value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${az.environment().suffixes.storage}'
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output id string = storageAccount.id
output name string = storageAccount.name
output primaryBlobEndpoint string = storageAccount.properties.primaryEndpoints.blob
output primaryDfsEndpoint string = storageAccount.properties.primaryEndpoints.dfs
