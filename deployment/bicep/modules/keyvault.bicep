// =============================================================================
// DA-MACAÉ :: Key Vault Module
// =============================================================================
// Azure Key Vault with RBAC, soft delete, purge protection
// =============================================================================

@description('Project name prefix')
param projectName string

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Azure region')
param location string

@description('Admin principal ID for initial access')
param adminObjectId string

@description('Resource tags')
param tags object

@description('Unique suffix to avoid naming conflicts')
param uniqueSuffix string

// ── Naming ────────────────────────────────────────────────────────────────

var envSuffix = environment == 'prod' ? '' : '-${environment}'
var keyVaultName = '${projectName}-kv-${uniqueSuffix}${envSuffix}'

// ── Key Vault ───────────────────────────────────────────────────────────────

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: environment == 'prod' ? 'premium' : 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: environment == 'prod' ? 90 : 30
    enablePurgeProtection: environment == 'prod' ? true : null
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    publicNetworkAccess: environment == 'prod' ? 'Disabled' : 'Enabled'
    networkAcls: environment == 'prod' ? {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
    } : {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

// ── Admin RBAC — Key Vault Administrator ────────────────────────────────────

resource adminRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, adminObjectId, 'Key Vault Administrator')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '00482a5a-887f-4fb3-b363-3b7fe8e74483')
    principalId: adminObjectId
    principalType: 'User'
  }
}

// ── Diagnostic Settings ─────────────────────────────────────────────────────

// Note: Log Analytics workspace ID should be passed if needed for diagnostics

// ── Outputs ─────────────────────────────────────────────────────────────────

output id string = keyVault.id
output name string = keyVault.name
output uri string = keyVault.properties.vaultUri
