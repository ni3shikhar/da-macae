// =============================================================================
// DA-MACAÉ v2 :: Monitoring Module
// =============================================================================
// Log Analytics Workspace + Application Insights (Python/FastAPI backend)
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
var logAnalyticsName = '${projectName}-log${envSuffix}'
var appInsightsName = '${projectName}-ai${envSuffix}'

// ── Configuration per environment ───────────────────────────────────────────

var retentionDays = environment == 'prod' ? 90 : 30
var dailyCapGb = environment == 'prod' ? 10 : environment == 'staging' ? 5 : 2
var sku = environment == 'prod' ? 'PerGB2018' : 'PerGB2018'

// ── Log Analytics Workspace ─────────────────────────────────────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: sku
    }
    retentionInDays: retentionDays
    workspaceCapping: {
      dailyQuotaGb: dailyCapGb
    }
    features: {
      enableDataExport: environment == 'prod'
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ── Application Insights ────────────────────────────────────────────────────

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    RetentionInDays: retentionDays
    SamplingPercentage: environment == 'prod' ? 50 : 100
    DisableIpMasking: false
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output logAnalyticsWorkspaceId string = logAnalytics.id
output logAnalyticsWorkspaceName string = logAnalytics.name
output appInsightsId string = appInsights.id
output appInsightsName string = appInsights.name
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
