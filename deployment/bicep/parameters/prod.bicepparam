using '../main.bicep'

param environment = 'prod'
param location = 'eastus2'
param projectName = 'damacae'
param adminObjectId = '' // Set via pipeline
param openAiModelDeployment = 'gpt-4o'
param tags = {
  project: 'da-macae'
  environment: 'prod'
  managedBy: 'bicep'
  costCenter: 'engineering'
  compliance: 'required'
  dataClassification: 'confidential'
}
