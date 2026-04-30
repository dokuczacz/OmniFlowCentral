#!/usr/bin/env pwsh
<#
.SYNOPSIS
Upgrade OmniFlowCentral Function App from FlexConsumption to Standard plan.
This enables static outbound IPs, allowing SAOS API connectivity.

.DESCRIPTION
This script:
1. Checks current plan configuration
2. Creates/scales Standard App Service Plan
3. Migrates Function App to new plan
4. Verifies outbound IPs are now static
5. Tests SAOS connectivity (optional)

.PARAMETER TargetSku
Target SKU: S1, S2, S3, P1V2, P2V2 (default: S1)

.PARAMETER Subscription
Azure Subscription ID (optional, uses default if not specified)

.EXAMPLE
.\upgrade_to_standard_plan.ps1 -TargetSku S1

.NOTES
- S1 is typically sufficient for SAOS queries
- Can be scaled up later if needed
- No data loss during migration
#>

param(
    [string]$TargetSku = "S1",
    [string]$Subscription = ""
)

$ErrorActionPreference = "Stop"

# Colors for output
$Success = "Green"
$Warning = "Yellow"
$Error = "Red"
$Info = "Cyan"

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    Write-Host $Message -ForegroundColor $Type
}

function Get-AppServicePlanName {
    Write-Status "Finding App Service Plan for OmniFlowCentral..." $Info
    
    $plan = az functionapp show `
        --name OmniFlowCentral `
        --resource-group AgentResourceGroup `
        --query appServicePlanId -o tsv | ForEach-Object { $_ -split '/' | Select-Object -Last 1 }
    
    if (-not $plan) {
        throw "Could not find App Service Plan"
    }
    
    Write-Status "Found: $plan" $Success
    return $plan
}

function Get-CurrentPlanInfo {
    param([string]$PlanName)
    
    Write-Status "Checking current plan configuration..." $Info
    
    $info = az appservice plan show `
        --name $PlanName `
        --resource-group AgentResourceGroup `
        --query "{name:name, sku:sku.tier, size:sku.size, kind:kind}" -o json | ConvertFrom-Json
    
    Write-Status "Current Plan: $($info.sku) ($($info.size))" $Info
    
    return $info
}

function Create-StandardPlan {
    param(
        [string]$PlanName,
        [string]$TargetSku
    )
    
    $newPlanName = "$PlanName-standard"
    
    Write-Status "Creating new Standard plan: $newPlanName" $Info
    
    $existing = az appservice plan list `
        --resource-group AgentResourceGroup `
        --query "[?name=='$newPlanName']" -o json | ConvertFrom-Json
    
    if ($existing.Count -gt 0) {
        Write-Status "Standard plan already exists: $newPlanName" $Warning
        return $newPlanName
    }
    
    az appservice plan create `
        --name $newPlanName `
        --resource-group AgentResourceGroup `
        --sku $TargetSku `
        --is-linux `
        --number-of-workers 1
    
    Write-Status "Created: $newPlanName" $Success
    return $newPlanName
}

function Migrate-FunctionApp {
    param(
        [string]$NewPlanName
    )
    
    Write-Status "Migrating OmniFlowCentral to $NewPlanName..." $Info
    
    az functionapp update `
        --name OmniFlowCentral `
        --resource-group AgentResourceGroup `
        --plan $NewPlanName
    
    Write-Status "Migration complete" $Success
}

function Verify-OutboundIPs {
    Write-Status "Verifying outbound IPs (may take 1-2 minutes)..." $Info
    
    $maxRetries = 6
    $retryCount = 0
    
    while ($retryCount -lt $maxRetries) {
        $ips = az functionapp show `
            --name OmniFlowCentral `
            --resource-group AgentResourceGroup `
            --query outboundIpAddresses -o tsv
        
        if ($ips -and $ips.Split(",").Count -gt 1) {
            Write-Status "Outbound IPs configured:" $Success
            $ips.Split(",") | ForEach-Object {
                Write-Host "  - $_"
            }
            return $true
        }
        
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Status "Waiting for IPs to propagate... ($retryCount/$maxRetries)" $Warning
            Start-Sleep -Seconds 10
        }
    }
    
    Write-Status "Warning: Outbound IPs not yet visible. They may take additional time to propagate." $Warning
    return $false
}

function Test-SaosConnectivity {
    Write-Status "Testing SAOS connectivity..." $Info
    
    $callUrl = $env:OMNIFLOW_CALL_URL
    if (-not $callUrl) {
        Write-Status "OMNIFLOW_CALL_URL not set. Skipping connectivity test." $Warning
        Write-Status "Set it manually and run: diagnose_saos_connectivity.py" $Info
        return
    }
    
    try {
        $payload = @{
            tool = "saos_search"
            payload = @{
                q = "konstytucja"
                limit = 1
            }
        } | ConvertTo-Json
        
        $response = Invoke-WebRequest `
            -Uri $callUrl `
            -Method Post `
            -ContentType "application/json" `
            -Body $payload `
            -TimeoutSec 30 `
            -ErrorAction Stop
        
        $data = $response.Content | ConvertFrom-Json
        
        if ($data.status -eq "success" -and $data.result.total_returned -gt 0) {
            Write-Status "✅ SAOS connectivity successful!" $Success
            Write-Status "Retrieved $($data.result.total_returned) judgment(s)" $Success
        }
        else {
            Write-Status "API responded but with unexpected result" $Warning
            Write-Host $data | ConvertTo-Json
        }
    }
    catch {
        Write-Status "Connectivity test failed (may still be propagating):" $Warning
        Write-Host $_.Exception.Message
    }
}

# Main execution
function Main {
    Write-Status "`n================================================`n" $Info
    Write-Status "OmniFlowCentral: Upgrade to Standard Plan" $Info
    Write-Status "================================================`n" $Info
    
    # Prerequisites
    Write-Status "Checking prerequisites..." $Info
    
    try {
        $account = az account show --query "name" -o tsv
        Write-Status "Logged in as: $account" $Success
    }
    catch {
        Write-Status "Please run: az login" $Error
        exit 1
    }
    
    # Get current state
    $currentPlan = Get-AppServicePlanName
    $planInfo = Get-CurrentPlanInfo $currentPlan
    
    if ($planInfo.sku -eq "Standard") {
        Write-Status "Already on Standard plan!" $Warning
        exit 0
    }
    
    # Create new standard plan
    $newPlan = Create-StandardPlan $currentPlan $TargetSku
    
    # Migrate
    Write-Status "Starting migration..." $Info
    Migrate-FunctionApp $newPlan
    
    # Verify
    Write-Status "Waiting for configuration to stabilize (60 seconds)..." $Info
    Start-Sleep -Seconds 60
    
    $ipsVerified = Verify-OutboundIPs
    
    # Test connectivity
    Write-Status "Testing connectivity..." $Info
    Test-SaosConnectivity
    
    # Summary
    Write-Status "`n================================================" $Success
    Write-Status "Upgrade Complete!" $Success
    Write-Status "================================================" $Success
    
    Write-Status "`nNext Steps:" $Info
    Write-Status "1. Run: python scripts\diagnose_saos_connectivity.py" $Info
    Write-Status "2. If still failing, check SAOS firewall rules" $Info
    Write-Status "3. Consider adding static IP to SAOS whitelist" $Info
    
    if (-not $ipsVerified) {
        Write-Status "`nNote: Outbound IPs may take 5-10 minutes to fully propagate." $Warning
    }
}

Main
