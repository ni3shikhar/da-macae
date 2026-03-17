// =============================================================================
// DA-MACAÉ v2 :: Azure Data Factory Module
// =============================================================================
// Provisions Azure Data Factory for data migration pipelines.
// Used by AdfPipelineGenerator agent for automated pipeline creation.
// =============================================================================

param projectName string
param environment string
param location string
param keyVaultName string
param tags object

// ── Naming Convention ───────────────────────────────────────────────────────

var envSuffix = environment == 'prod' ? '' : '-${environment}'
var adfName = '${projectName}adf${envSuffix}'

// ── Azure Data Factory ──────────────────────────────────────────────────────

resource dataFactory 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: adfName
  location: location
  tags: tags
  properties: {
    publicNetworkAccess: 'Enabled'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ── Role Assignment for Data Factory to access Key Vault ───────────────────

resource keyVaultAccess 'Microsoft.KeyVault/vaults/accessPolicies@2023-07-01' = {
  name: '${keyVaultName}/add'
  properties: {
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: dataFactory.identity.principalId
        permissions: {
          secrets: [
            'get'
            'list'
          ]
          certificates: []
          keys: []
        }
      }
    ]
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output name string = dataFactory.name
output id string = dataFactory.id
output principalId string = dataFactory.identity.principalId
