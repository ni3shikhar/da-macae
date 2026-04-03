<#
.SYNOPSIS
    Deploy AGENTRA (DA-MACAE v2) to Azure

.DESCRIPTION
    This script deploys the AGENTRA solution to Azure using Azure Developer CLI (azd).
    It provisions all required infrastructure and deploys the containerized services.

.PARAMETER Environment
    Target environment: dev, staging, or prod (default: dev)

.PARAMETER Location
    Azure region (default: eastus2)

.PARAMETER SkipInfra
    Skip infrastructure provisioning, only deploy containers

.PARAMETER SkipBuild
    Skip Docker image builds, use existing images

.EXAMPLE
    .\deploy.ps1 -Environment dev
    
.EXAMPLE
    .\deploy.ps1 -Environment prod -Location westus2
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet('dev', 'staging', 'prod')]
    [string]$Environment = 'dev',

    [Parameter()]
    [string]$Location = 'eastus2',

    [Parameter()]
    [string]$SubscriptionId,

    [Parameter()]
    [switch]$SkipInfra,

    [Parameter()]
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$ScriptRoot = $PSScriptRoot

# ==============================================================================
# Configuration
# ==============================================================================
$ProjectName = 'damacae'
$RequiredTools = @('az', 'azd', 'docker')

# ==============================================================================
# Helper Functions
# ==============================================================================

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host "===============================================================" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host "> $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Gray
}

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Get-UserObjectId {
    $objectId = az ad signed-in-user show --query id -o tsv 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to get user object ID. Ensure you're logged into Azure CLI."
    }
    return $objectId.Trim()
}

# ==============================================================================
# Prerequisites Check
# ==============================================================================

function Test-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    $missing = @()
    foreach ($tool in $RequiredTools) {
        if (Test-Command $tool) {
            Write-Success "$tool is installed"
        } else {
            $missing += $tool
        }
    }

    if ($missing.Count -gt 0) {
        Write-Host ""
        Write-Host "Missing required tools:" -ForegroundColor Red
        foreach ($tool in $missing) {
            Write-Host "  - $tool" -ForegroundColor Red
        }
        Write-Host ""
        Write-Host "Installation instructions:" -ForegroundColor Yellow
        Write-Host "  az  : https://docs.microsoft.com/cli/azure/install-azure-cli"
        Write-Host "  azd : https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd"
        Write-Host "  docker: https://docs.docker.com/desktop/install/windows-install/"
        throw "Please install missing tools and try again."
    }

    # Check Docker is running
    Write-Step "Checking Docker daemon..."
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is not running. Please start Docker Desktop and try again."
    }
    Write-Success "Docker is running"
}

# ==============================================================================
# Azure Authentication
# ==============================================================================

function Connect-Azure {
    Write-Header "Azure Authentication"

    # Check Azure CLI login
    Write-Step "Checking Azure CLI authentication..."
    $account = az account show 2>$null | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Not logged in. Initiating Azure CLI login..."
        az login
        if ($LASTEXITCODE -ne 0) { throw "Azure CLI login failed" }
        $account = az account show | ConvertFrom-Json
    }

    if ($SubscriptionId) {
        Write-Step "Setting Azure subscription to '$SubscriptionId'..."
        az account set --subscription $SubscriptionId
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to set Azure subscription '$SubscriptionId'"
        }
        $account = az account show | ConvertFrom-Json
    }

    if (-not $account) {
        throw "Unable to read Azure account. Ensure az login is successful."
    }

    Write-Success "Azure CLI: $($account.user.name) @ $($account.name)"

    # Ensure subscription is selected
    if (-not $account.id) {
        throw "Azure subscription not selected. Run az account set --subscription <id> or provide -SubscriptionId to deploy.ps1."
    }

    Write-Success "Azure subscription: $($account.name) ($($account.id))"

    # Check AZD login
    Write-Step "Checking Azure Developer CLI authentication..."
    $azdAuth = azd auth login --check-status 2>&1
    if ($azdAuth -notmatch "Logged in") {
        Write-Info "Not logged in. Initiating AZD login..."
        azd auth login
        if ($LASTEXITCODE -ne 0) { throw "AZD login failed" }
    }
    Write-Success "Azure Developer CLI authenticated"

    return $account
}

# ==============================================================================
# Environment Setup
# ==============================================================================

function Initialize-Environment {
    param([string]$Env, [string]$Loc)
    
    Write-Header "Environment Setup: $Env"

    Set-Location $ScriptRoot
    
    # Get user's object ID for Key Vault access
    Write-Step "Getting Azure AD user object ID..."
    $userObjectId = Get-UserObjectId
    Write-Success "User Object ID: $userObjectId"

    # Check if environment exists, if not create it
    Write-Step "Initializing AZD environment '$Env'..."
    $envList = azd env list --output json 2>$null | ConvertFrom-Json
    $envExists = $envList | Where-Object { $_.Name -eq $Env }
    
    if (-not $envExists) {
        azd env new $Env
        if ($LASTEXITCODE -ne 0) { throw "Failed to create AZD environment" }
    }
    azd env select $Env
    Write-Success "Environment '$Env' selected"

    # Set environment variables
    Write-Step "Configuring environment variables..."
    azd env set AZURE_LOCATION $Loc
    azd env set AZURE_ENV_NAME $Env
    azd env set ADMIN_OBJECT_ID $userObjectId
    azd env set PROJECT_NAME $ProjectName
    
    # Check for .env file with secrets
    $envFile = Join-Path $ScriptRoot ".env.$Env"
    if (Test-Path $envFile) {
        Write-Info "Loading secrets from $envFile"
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^([^#=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                if ($value -and $key -notmatch '^#') {
                    azd env set $key $value
                }
            }
        }
    } else {
        Write-Info "No .env.$Env file found. You may need to set secrets manually."
        Write-Info "Create $envFile with required secrets (see .env.template)"
    }

    Write-Success "Environment configured"
}

# ==============================================================================
# Infrastructure Deployment
# ==============================================================================

function Deploy-Infrastructure {
    param([string]$Env)
    
    Write-Header "Deploying Infrastructure"
    
    Write-Step "Provisioning Azure resources..."
    Write-Info "This may take 10-20 minutes for initial deployment"
    
    azd provision --environment $Env
    if ($LASTEXITCODE -ne 0) { throw "Infrastructure provisioning failed" }
    
    Write-Success "Infrastructure deployed successfully"
}

# ==============================================================================
# Application Deployment
# ==============================================================================

function Deploy-Applications {
    param([string]$Env, [bool]$Build)
    
    Write-Header "Deploying Applications"

    if ($Build) {
        Write-Step "Building and deploying containers..."
        azd deploy --environment $Env
    } else {
        Write-Step "Deploying containers (skip build)..."
        azd deploy --environment $Env --no-build
    }
    
    if ($LASTEXITCODE -ne 0) { throw "Application deployment failed" }
    
    Write-Success "Applications deployed successfully"
}

# ==============================================================================
# Post-Deployment
# ==============================================================================

function Show-DeploymentInfo {
    param([string]$Env)
    
    Write-Header "Deployment Complete!"
    
    Write-Step "Retrieving deployment endpoints..."
    
    # Get outputs from azd
    $outputs = azd env get-values --environment $Env | ConvertFrom-StringData
    
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Green
    Write-Host " AGENTRA Deployment Summary" -ForegroundColor Green
    Write-Host "===============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Environment:    $Env" -ForegroundColor White
    Write-Host "  Resource Group: $ProjectName-rg$(if ($Env -ne 'prod') { "-$Env" })" -ForegroundColor White
    Write-Host ""
    
    # Try to get service endpoints
    $services = azd show --environment $Env --output json 2>$null | ConvertFrom-Json
    if ($services.services) {
        Write-Host "  Service Endpoints:" -ForegroundColor Yellow
        foreach ($svc in $services.services.PSObject.Properties) {
            if ($svc.Value.endpoint) {
                Write-Host "    $($svc.Name): $($svc.Value.endpoint)" -ForegroundColor Cyan
            }
        }
    }
    
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Yellow
    Write-Host "  azd monitor --environment $Env    # View logs and metrics"
    Write-Host "  azd down --environment $Env       # Tear down resources"
    Write-Host "  azd deploy --environment $Env     # Redeploy applications"
    Write-Host ""
}

# ==============================================================================
# Main Execution
# ==============================================================================

try {
    Write-Host ""
    Write-Host "    _    ____ _____ _   _ _____ ____    _    " -ForegroundColor Magenta
    Write-Host "   / \  / ___| ____| \ | |_   _|  _ \  / \   " -ForegroundColor Magenta
    Write-Host "  / _ \| |  _|  _| |  \| | | | | |_) |/ _ \  " -ForegroundColor Magenta
    Write-Host " / ___ \ |_| | |___| |\  | | | |  _ </ ___ \ " -ForegroundColor Magenta
    Write-Host "/_/   \_\____|_____|_| \_| |_| |_| \_\_/   \_\" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "   Azure Deployment Script v1.0" -ForegroundColor DarkGray
    Write-Host ""

    # Step 1: Check prerequisites
    Test-Prerequisites

    # Step 2: Authenticate
    $azAccount = Connect-Azure

    # Step 3: Initialize environment
    Initialize-Environment -Env $Environment -Loc $Location

    # Step 4: Deploy infrastructure (unless skipped)
    if (-not $SkipInfra) {
        Deploy-Infrastructure -Env $Environment
    } else {
        Write-Info "Skipping infrastructure provisioning (--SkipInfra)"
    }

    # Step 5: Deploy applications
    Deploy-Applications -Env $Environment -Build (-not $SkipBuild)

    # Step 6: Show deployment info
    Show-DeploymentInfo -Env $Environment

} catch {
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Red
    Write-Host " Deployment Failed" -ForegroundColor Red
    Write-Host "===============================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "For troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check Azure portal for resource status"
    Write-Host "  2. Run: azd monitor --environment $Environment"
    Write-Host "  3. Check logs: azd deploy --environment $Environment --debug"
    Write-Host ""
    exit 1
}
