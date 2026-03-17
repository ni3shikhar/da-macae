// =============================================================================
// DA-MACAÉ :: Azure OpenAI Module
// =============================================================================
// Cognitive Services account with GPT-4o deployment
// =============================================================================

@description('Project name prefix')
param projectName string

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Azure region')
param location string

@description('Model deployment name')
param modelDeployment string

@description('Key Vault name for storing connection secrets')
param keyVaultName string

@description('Resource tags')
param tags object

// ── Naming ──────────────────────────────────────────────────────────────────

var envSuffix = environment == 'prod' ? '' : '-${environment}'
var openAiName = '${projectName}-openai${envSuffix}'

// ── Configuration per environment ───────────────────────────────────────────

var capacityConfig = {
  dev: { tpmCapacity: 30, skuName: 'S0' }
  staging: { tpmCapacity: 60, skuName: 'S0' }
  prod: { tpmCapacity: 120, skuName: 'S0' }
}

// ── Azure OpenAI Account ────────────────────────────────────────────────────

resource openAi 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: openAiName
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: capacityConfig[environment].skuName
  }
  properties: {
    customSubDomainName: openAiName
    publicNetworkAccess: environment == 'prod' ? 'Disabled' : 'Enabled'
    networkAcls: environment == 'prod' ? {
      defaultAction: 'Deny'
    } : {
      defaultAction: 'Allow'
    }
    disableLocalAuth: false
  }
}

// ── GPT-4o Deployment ───────────────────────────────────────────────────────

resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAi
  name: modelDeployment
  sku: {
    name: 'Standard'
    capacity: capacityConfig[environment].tpmCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
    raiPolicyName: 'Microsoft.Default'
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

// ── Text Embedding Deployment ───────────────────────────────────────────────

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAi
  name: 'text-embedding-3-small'
  sku: {
    name: 'Standard'
    capacity: environment == 'prod' ? 120 : 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
    raiPolicyName: 'Microsoft.Default'
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
  dependsOn: [gpt4oDeployment]
}

// ── Store secrets in Key Vault ──────────────────────────────────────────────

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource openAiEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'azure-openai-endpoint'
  properties: {
    value: openAi.properties.endpoint
  }
}

resource openAiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'azure-openai-api-key'
  properties: {
    value: openAi.listKeys().key1
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output id string = openAi.id
output name string = openAi.name
output endpoint string = openAi.properties.endpoint
output gpt4oDeploymentName string = gpt4oDeployment.name
output embeddingDeploymentName string = embeddingDeployment.name
