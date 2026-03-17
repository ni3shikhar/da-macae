using '../main.bicep'

param environment = 'dev'
param location = 'eastus2'
param projectName = 'damacae'
param adminObjectId = '' // Set via pipeline: az ad signed-in-user show --query id -o tsv
param openAiModelDeployment = 'gpt-4o'
param tags = {
  project: 'da-macae'
  environment: 'dev'
  managedBy: 'bicep'
  costCenter: 'engineering'
}
