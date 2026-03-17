using '../main.bicep'

param environment = 'staging'
param location = 'eastus2'
param projectName = 'damacae'
param adminObjectId = '' // Set via pipeline
param openAiModelDeployment = 'gpt-4o'
param tags = {
  project: 'da-macae'
  environment: 'staging'
  managedBy: 'bicep'
  costCenter: 'engineering'
}
