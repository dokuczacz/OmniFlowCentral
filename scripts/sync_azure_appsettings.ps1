param(
  [Parameter(Mandatory = $true)]
  [string]$ResourceGroup,

  [Parameter(Mandatory = $false)]
  [string]$FunctionAppName = "OmniFlowCentral",

  [Parameter(Mandatory = $false)]
  [string]$SettingsFile,

  [switch]$DryRun,

  [switch]$NoRestart,

  [switch]$NoProdRedirectUri
)

$ErrorActionPreference = "Stop"

function Resolve-DefaultSettingsFile {
  if ($SettingsFile -and (Test-Path -LiteralPath $SettingsFile)) {
    return (Resolve-Path -LiteralPath $SettingsFile).Path
  }

  $candidates = @(
    (Join-Path $PSScriptRoot "..\\OmniFlowCentral\\local.settings.json"),
    (Join-Path $PSScriptRoot "..\\OmniFlowCentral\\local.settings.template.json")
  )
  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) {
      return (Resolve-Path -LiteralPath $candidate).Path
    }
  }
  throw "No settings file found. Provide -SettingsFile pointing to local.settings.json or local.settings.template.json."
}

function Require-AzCli {
  $az = Get-Command az -ErrorAction SilentlyContinue
  if (-not $az) {
    throw "Azure CLI (az) not found in PATH. Install it first: https://learn.microsoft.com/cli/azure/install-azure-cli"
  }
  try {
    az account show --only-show-errors --output none | Out-Null
  } catch {
    throw "Azure CLI not logged in. Run: az login"
  }
}

function Load-SettingsJson([string]$path) {
  $raw = Get-Content -LiteralPath $path -Raw
  $json = $raw | ConvertFrom-Json
  if ($null -ne $json.Values) {
    return $json.Values
  }
  return $json
}

function Get-DefaultHostName([string]$rg, [string]$app) {
  $defaultHostName = az functionapp show -g $rg -n $app --query properties.defaultHostName -o tsv --only-show-errors
  if (-not $defaultHostName) {
    throw "Unable to read defaultHostName for Function App '$app' in RG '$rg'."
  }
  return $defaultHostName.Trim()
}

$requiredKeys = @(
  "AzureWebJobsStorage",
  "AZURE_STORAGE_CONNECTION_STRING",
  "AZURE_BLOB_CONTAINER_NAME",
  "OMNIFLOWCENTRAL_OAUTH_CONTAINER_NAME",
  "GMAIL_OAUTH_CLIENT_ID",
  "GMAIL_OAUTH_CLIENT_SECRET"
)

$optionalKeys = @(
  "GMAIL_OAUTH_SCOPES",
  "GMAIL_OAUTH_PROMPT",
  "OMNIFLOW_DEBUG",
  "AZURE_SDK_LOG_LEVEL",
  "AZURE_HTTP_LOGGING"
)

Require-AzCli
$settingsPath = Resolve-DefaultSettingsFile
$values = Load-SettingsJson $settingsPath

$desired = @{}
foreach ($key in ($requiredKeys + $optionalKeys + @("GMAIL_OAUTH_REDIRECT_URI"))) {
  if ($null -ne $values.$key -and ("" + $values.$key).Trim().Length -gt 0) {
    $desired[$key] = ("" + $values.$key).Trim()
  }
}

if (-not $desired.ContainsKey("AZURE_BLOB_CONTAINER_NAME")) {
  $desired["AZURE_BLOB_CONTAINER_NAME"] = "omniflowcentralcustomgpt"
}
if (-not $desired.ContainsKey("OMNIFLOWCENTRAL_OAUTH_CONTAINER_NAME")) {
  $desired["OMNIFLOWCENTRAL_OAUTH_CONTAINER_NAME"] = "omniflowcentraloauth"
}

if (-not $desired.ContainsKey("AzureWebJobsStorage") -and $desired.ContainsKey("AZURE_STORAGE_CONNECTION_STRING")) {
  $desired["AzureWebJobsStorage"] = $desired["AZURE_STORAGE_CONNECTION_STRING"]
}
if (-not $desired.ContainsKey("AZURE_STORAGE_CONNECTION_STRING") -and $desired.ContainsKey("AzureWebJobsStorage")) {
  $desired["AZURE_STORAGE_CONNECTION_STRING"] = $desired["AzureWebJobsStorage"]
}

if (-not $NoProdRedirectUri) {
  $defaultHostName = Get-DefaultHostName -rg $ResourceGroup -app $FunctionAppName
  $desired["GMAIL_OAUTH_REDIRECT_URI"] = "https://$defaultHostName/api/gmail_oauth_callback"
}

$missing = @()
foreach ($key in $requiredKeys) {
  if (-not $desired.ContainsKey($key) -or -not $desired[$key]) {
    $missing += $key
  }
}

Write-Host "Settings source: $settingsPath"
Write-Host "Target Function App: $FunctionAppName (RG: $ResourceGroup)"
Write-Host "Will set $($desired.Keys.Count) app settings (values are not printed):"
$desired.Keys | Sort-Object | ForEach-Object { Write-Host "  - $_" }

if ($missing.Count -gt 0) {
  throw ("Missing required keys in settings source: " + ($missing -join ", "))
}

if ($DryRun) {
  Write-Host "DryRun: not applying settings."
  exit 0
}

$pairs = @()
foreach ($k in $desired.Keys) {
  $pairs += ("{0}={1}" -f $k, $desired[$k])
}

az functionapp config appsettings set -g $ResourceGroup -n $FunctionAppName --settings @pairs --only-show-errors --output none | Out-Null

if (-not $NoRestart) {
  az functionapp restart -g $ResourceGroup -n $FunctionAppName --only-show-errors | Out-Null
}

Write-Host "Done."
