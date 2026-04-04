// =============================================================================
// DA-MACAÉ :: Container Registry Module
// =============================================================================
// Azure Container Registry for Docker images
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

@description('Unique suffix to avoid naming conflicts')
param uniqueSuffix string

// ── Naming ────────────────────────────────────────────────────────────────

// ACR names must be alphanumeric only, globally unique
var envTag = environment == 'prod' ? '' : environment
var acrName = '${projectName}acr${uniqueSuffix}${envTag}'

// ── Configuration per environment ───────────────────────────────────────────

var skuName = environment == 'prod' ? 'Premium' : 'Basic'

// ── Container Registry ──────────────────────────────────────────────────────

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: environment == 'prod' ? 'Disabled' : 'Enabled'
    zoneRedundancy: environment == 'prod' ? 'Enabled' : 'Disabled'
    policies: {
      retentionPolicy: {
        status: environment == 'prod' ? 'enabled' : 'disabled'
        days: 30
      }
      trustPolicy: {
        status: environment == 'prod' ? 'enabled' : 'disabled'
        type: 'Notary'
      }
      quarantinePolicy: {
        status: 'disabled'
      }
    }
    encryption: {
      status: 'disabled'
    }
    dataEndpointEnabled: false
  }
}

// ── Geo-replication (Premium only, prod) ────────────────────────────────────

resource geoReplication 'Microsoft.ContainerRegistry/registries/replications@2023-11-01-preview' = if (environment == 'prod') {
  parent: acr
  name: 'westus2'
  location: 'westus2'
  properties: {
    zoneRedundancy: 'Enabled'
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output id string = acr.id
output name string = acr.name
output loginServer string = acr.properties.loginServer
