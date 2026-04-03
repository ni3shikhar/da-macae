// =============================================================================
// DA-MACAÉ v2 :: Cosmos DB Module
// =============================================================================
// NoSQL account with database and containers for session-based state.
// V2 uses a single "sessions" container partitioned by /user_id with
// document types: session, plan, m_plan, agent_message, team_config,
// user_current_team.
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

var envSuffix = environment == 'prod' ? '' : '-${environment}'
var accountName = '${projectName}-cosmos${envSuffix}'
var databaseName = 'damacae'

// ── Configuration per environment ───────────────────────────────────────────

var consistencyLevel = environment == 'prod' ? 'BoundedStaleness' : 'Session'
var maxThroughput = environment == 'prod' ? 10000 : environment == 'staging' ? 4000 : 1000
var enableMultiRegion = environment == 'prod'
var backupType = environment == 'prod' ? 'Continuous' : 'Periodic'

// ── Cosmos DB Account ───────────────────────────────────────────────────────

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: consistencyLevel == 'BoundedStaleness' ? {
      defaultConsistencyLevel: consistencyLevel
      maxStalenessPrefix: 100000
      maxIntervalInSeconds: 300
    } : {
      defaultConsistencyLevel: consistencyLevel
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: environment == 'prod'
      }
    ]
    enableAutomaticFailover: enableMultiRegion
    enableMultipleWriteLocations: false
    isVirtualNetworkFilterEnabled: false
    publicNetworkAccess: environment == 'prod' ? 'Disabled' : 'Enabled'
    disableLocalAuth: false
    backupPolicy: backupType == 'Continuous' ? {
      type: 'Continuous'
      continuousModeProperties: {
        tier: 'Continuous30Days'
      }
    } : {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 8
        backupStorageRedundancy: 'Local'
      }
    }
    capacity: {
      totalThroughputLimit: maxThroughput * 2
    }
    minimalTlsVersion: 'Tls12'
  }
}

// ── Database ────────────────────────────────────────────────────────────────

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// ── Container: sessions (V2 primary container) ─────────────────────────────
// Stores all session-scoped documents: sessions, plans, agent messages,
// team configurations. Partitioned by user_id for per-user data isolation.

resource sessionsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'sessions'
  properties: {
    resource: {
      id: 'sessions'
      partitionKey: {
        paths: ['/user_id']
        kind: 'Hash'
        version: 2
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          { path: '/*' }
        ]
        excludedPaths: [
          { path: '/"_etag"/?' }
        ]
        compositeIndexes: [
          [
            { path: '/type', order: 'ascending' }
            { path: '/created_at', order: 'descending' }
          ]
          [
            { path: '/user_id', order: 'ascending' }
            { path: '/session_id', order: 'ascending' }
          ]
          [
            { path: '/status', order: 'ascending' }
            { path: '/created_at', order: 'descending' }
          ]
        ]
      }
      defaultTtl: -1
      uniqueKeyPolicy: {
        uniqueKeys: [
          { paths: ['/session_id'] }
        ]
      }
    }
    options: {
      autoscaleSettings: {
        maxThroughput: maxThroughput
      }
    }
  }
}

// ── Store secrets in Key Vault ──────────────────────────────────────────────

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource cosmosEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'azure-cosmos-endpoint'
  properties: {
    value: cosmosAccount.properties.documentEndpoint
  }
}

resource cosmosKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'azure-cosmos-key'
  properties: {
    value: cosmosAccount.listKeys().primaryMasterKey
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output id string = cosmosAccount.id
output name string = cosmosAccount.name
output endpoint string = cosmosAccount.properties.documentEndpoint
output databaseName string = database.name
