// =============================================================================
// DA-MACAÉ v2 :: Service Bus Module
// =============================================================================
// Service Bus namespace with queues for async event processing.
// V2 uses WebSocket for real-time UI updates; Service Bus handles
// background async events, dead-letter processing, and audit trails.
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
var namespaceName = '${projectName}-sb${envSuffix}'

// ── Configuration per environment ───────────────────────────────────────────

var skuConfig = {
  dev: { name: 'Basic', tier: 'Basic' }
  staging: { name: 'Standard', tier: 'Standard' }
  prod: { name: 'Premium', tier: 'Premium', capacity: 1 }
}

// ── Service Bus Namespace ───────────────────────────────────────────────────

resource serviceBus 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: namespaceName
  location: location
  tags: tags
  sku: {
    name: skuConfig[environment].name
    tier: skuConfig[environment].tier
    capacity: environment == 'prod' ? skuConfig[environment].capacity : null
  }
  properties: {
    zoneRedundant: environment == 'prod'
    minimumTlsVersion: '1.2'
    publicNetworkAccess: environment == 'prod' ? 'Disabled' : 'Enabled'
    disableLocalAuth: false
    premiumMessagingPartitions: environment == 'prod' ? 1 : null
  }
}

// ── Queue: dead-letter ──────────────────────────────────────────────────────

resource deadLetterQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBus
  name: 'da-macae-dead-letter'
  properties: {
    lockDuration: 'PT5M'
    maxSizeInMegabytes: environment == 'prod' ? 5120 : 1024
    requiresDuplicateDetection: true
    duplicateDetectionHistoryTimeWindow: 'PT10M'
    deadLetteringOnMessageExpiration: true
    defaultMessageTimeToLive: 'P14D'
    maxDeliveryCount: 10
    enableBatchedOperations: true
    autoDeleteOnIdle: 'P365D'
  }
}

// ── Queue: migration-events ─────────────────────────────────────────────────

resource migrationEventsQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = if (environment != 'dev') {
  parent: serviceBus
  name: 'da-macae-migration-events'
  properties: {
    lockDuration: 'PT5M'
    maxSizeInMegabytes: environment == 'prod' ? 5120 : 1024
    requiresDuplicateDetection: false
    deadLetteringOnMessageExpiration: true
    defaultMessageTimeToLive: 'P7D'
    maxDeliveryCount: 5
    enableBatchedOperations: true
    forwardDeadLetteredMessagesTo: deadLetterQueue.name
  }
}

// ── Topic: workflow-notifications (Standard/Premium only) ───────────────────

resource notificationsTopic 'Microsoft.ServiceBus/namespaces/topics@2022-10-01-preview' = if (environment != 'dev') {
  parent: serviceBus
  name: 'da-macae-workflow-notifications'
  properties: {
    maxSizeInMegabytes: 1024
    defaultMessageTimeToLive: 'P7D'
    duplicateDetectionHistoryTimeWindow: 'PT10M'
    enableBatchedOperations: true
    requiresDuplicateDetection: true
  }
}

// ── Store secrets in Key Vault ──────────────────────────────────────────────

var authRuleId = resourceId('Microsoft.ServiceBus/namespaces/authorizationRules', namespaceName, 'RootManageSharedAccessKey')

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource sbConnectionSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'azure-servicebus-connection-string'
  properties: {
    value: listKeys(authRuleId, '2022-10-01-preview').primaryConnectionString
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output id string = serviceBus.id
output namespaceName string = serviceBus.name
output deadLetterQueueName string = deadLetterQueue.name
