# AGENTRA - GitHub Actions Deployment Setup

## Overview

This project uses two GitHub Actions workflows:
- **CI** (`ci.yml`) - Build & test on every PR/push
- **CD** (`cd.yml`) - Deploy to Azure on merge to develop/main

### Deployment Flow

```
develop branch  -->  auto-deploy to DEV
main branch     -->  auto-deploy to STAGING  -->  manual approval  -->  PROD
manual trigger  -->  deploy to chosen environment
```

---

## Step 1: Create Azure Service Principal (OIDC)

Use federated credentials (no secrets stored):

```bash
# Create an App Registration
az ad app create --display-name "agentra-github-deploy"

# Note the appId from output, then create a service principal
az ad sp create --id <APP_ID>

# Get the service principal object ID
az ad sp show --id <APP_ID> --query id -o tsv

# Assign Contributor + User Access Administrator on target subscription
az role assignment create \
  --assignee <APP_ID> \
  --role "Contributor" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>"

az role assignment create \
  --assignee <APP_ID> \
  --role "User Access Administrator" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>"
```

## Step 2: Configure Federated Credentials

In Azure Portal:
1. Go to **App registrations** > your app > **Certificates & secrets**
2. Click **Federated credentials** > **Add credential**
3. Select **GitHub Actions deploying Azure resources**
4. Configure:

| Field | Value |
|-------|-------|
| Organization | `<your-github-org>` |
| Repository | `<your-repo-name>` |
| Entity type | Environment |
| Environment name | `dev` |

Repeat for `staging` and `prod` environments.

For branch-based triggers, also add:
| Entity type | Branch |
|-------------|--------|
| Branch | `main` |
| Branch | `develop` |

## Step 3: Create GitHub Environments

In your GitHub repo: **Settings > Environments**

### Create 3 environments:

#### `dev`
- No protection rules needed

#### `staging`
- Optional: required reviewers

#### `prod`
- **Required**: Add required reviewers (at least 1 approver)
- Optional: deployment branches = `main` only

## Step 4: Configure GitHub Secrets

Go to **Settings > Secrets and variables > Actions**

### Repository Secrets (shared across environments):

| Secret | Value | How to get it |
|--------|-------|---------------|
| `AZURE_CLIENT_ID` | App Registration Application (client) ID | `az ad app list --display-name agentra-github-deploy --query [0].appId -o tsv` |
| `AZURE_TENANT_ID` | Azure AD Tenant ID | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription ID | `az account show --query id -o tsv` |
| `ADMIN_OBJECT_ID` | Admin user/SP object ID for Key Vault/AKS | `az ad signed-in-user show --query id -o tsv` |

### Repository Variables:

| Variable | Value | Example |
|----------|-------|---------|
| `AZURE_LOCATION` | Azure region | `eastus2` |
| `ACR_NAME` | Container Registry name | `damacaeacr` (set after first infra deploy) |
| `ACR_LOGIN_SERVER` | ACR login server | `damacaeacr.azurecr.io` (set after first infra deploy) |

> **Note**: ACR_NAME and ACR_LOGIN_SERVER are created during infrastructure provisioning.
> After first `azd provision`, get them with:
> ```bash
> az acr list --resource-group damacae-rg-dev --query [0].name -o tsv
> az acr list --resource-group damacae-rg-dev --query [0].loginServer -o tsv
> ```

## Step 5: First Deployment

### Option A: Manual trigger (recommended for first time)

1. Go to **Actions** tab in GitHub
2. Select **CD - Deploy to Azure**
3. Click **Run workflow**
4. Select environment: `dev`
5. Keep "Skip infrastructure" unchecked
6. Click **Run workflow**

### Option B: Push to develop branch

```bash
git checkout develop
git push origin develop
```

This auto-triggers deployment to `dev`.

## Step 6: After First Infrastructure Deploy

Once infrastructure is provisioned, update these GitHub variables:

```bash
# Get ACR details from the deployed resource group
ACR_NAME=$(az acr list -g damacae-rg-dev --query [0].name -o tsv)
ACR_SERVER=$(az acr list -g damacae-rg-dev --query [0].loginServer -o tsv)

echo "ACR_NAME: $ACR_NAME"
echo "ACR_LOGIN_SERVER: $ACR_SERVER"
```

Update `ACR_NAME` and `ACR_LOGIN_SERVER` in GitHub repo variables.

---

## Troubleshooting

### "AADSTS700024: Client assertion is not within its valid time range"
- Federated credential entity type doesn't match. Check environment name matches exactly.

### "The subscription is not registered to use namespace 'Microsoft.App'"
```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
```

### "Soft-deleted Key Vault conflict"
```bash
az keyvault purge --name damacae-kv-dev --location eastus2
```

### ACR login fails
- Ensure the service principal has `AcrPush` role on the ACR:
```bash
ACR_ID=$(az acr show --name <ACR_NAME> --query id -o tsv)
az role assignment create --assignee <APP_ID> --role AcrPush --scope $ACR_ID
```
