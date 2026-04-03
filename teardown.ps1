<#
.SYNOPSIS
    Tear down AGENTRA Azure resources

.DESCRIPTION
    This script removes all Azure resources deployed for the AGENTRA solution.
    USE WITH CAUTION - this will permanently delete resources!

.PARAMETER Environment
    Target environment to tear down: dev, staging, or prod

.PARAMETER Force
    Skip confirmation prompt

.PARAMETER Purge
    Also purge soft-deleted Key Vault and Azure OpenAI resources

.EXAMPLE
    .\teardown.ps1 -Environment dev
    
.EXAMPLE
    .\teardown.ps1 -Environment dev -Force -Purge
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('dev', 'staging', 'prod')]
    [string]$Environment,

    [Parameter()]
    [switch]$Force,

    [Parameter()]
    [switch]$Purge
)

$ErrorActionPreference = 'Stop'
$ScriptRoot = $PSScriptRoot
$ProjectName = 'damacae'

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host " $Message" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Red
}

function Write-Step {
    param([string]$Message)
    Write-Host "► $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

try {
    Write-Header "AGENTRA Resource Teardown"
    
    $rgName = "$ProjectName-rg$(if ($Environment -ne 'prod') { "-$Environment" })"
    
    Write-Host ""
    Write-Host "  Environment:    $Environment" -ForegroundColor White
    Write-Host "  Resource Group: $rgName" -ForegroundColor White
    Write-Host ""
    
    if (-not $Force) {
        Write-Host "WARNING: This will permanently delete all resources!" -ForegroundColor Red
        Write-Host ""
        $confirm = Read-Host "Type 'DELETE' to confirm"
        if ($confirm -ne 'DELETE') {
            Write-Host "Aborted." -ForegroundColor Yellow
            exit 0
        }
    }
    
    Set-Location $ScriptRoot
    
    Write-Step "Selecting environment..."
    azd env select $Environment 2>$null
    
    Write-Step "Tearing down Azure resources..."
    if ($Purge) {
        azd down --environment $Environment --purge --force
    } else {
        azd down --environment $Environment --force
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Teardown failed"
    }
    
    Write-Host ""
    Write-Success "All resources for '$Environment' have been deleted."
    
    if (-not $Purge) {
        Write-Host ""
        Write-Host "Note: Key Vault and Azure OpenAI may be soft-deleted." -ForegroundColor Yellow
        Write-Host "Run with -Purge flag to permanently remove them." -ForegroundColor Yellow
    }
    
} catch {
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
