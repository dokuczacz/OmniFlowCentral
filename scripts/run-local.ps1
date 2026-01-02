<#
.SYNOPSIS
  Start OmniFlowCentral locally (venv, azurite optional, func host) and capture logs.

.DESCRIPTION
  This helper mirrors the repo's existing "run locally" pattern.
  - Activates a virtual environment if found (.venv or .venv in parent folders)
  - Optionally starts Azurite for local Blob Storage
  - Starts the Azure Functions host for the `OmniFlowCentral` function app and
    redirects stdout/stderr to a log file
  - Optionally waits for the health endpoint and runs the integration smoke
    tests (writes pytest output to `tests-integration.log`).

.PARAMETER StartAzurite
  Start Azurite (if available on PATH).

.PARAMETER RunTests
  After the host is healthy, run `pytest tests/integration` and write results to `tests-integration.log`.

.PARAMETER Port
  Port for Functions host (default 7071).

.PARAMETER LogFile
  Path to write the Functions host stdout/stderr (default: ./omniflowcentral-run.log).

Examples:
  # start host and write logs
  .\scripts\run-local.ps1

  # start azurite and run integration tests when healthy
  .\scripts\run-local.ps1 -StartAzurite -RunTests
#>

param(
    [switch]$StartAzurite = $false,
    [switch]$RunTests = $false,
    [int]$Port = 7071,
    [string]$LogFile = "./omniflowcentral-run.log"
)

function Activate-Venv {
    $candidates = @(
        "$PSScriptRoot\..\.venv\Scripts\Activate.ps1",
        "$PSScriptRoot\..\..\.venv\Scripts\Activate.ps1",
        "$PSScriptRoot\..\OmniFlowCentral\.venv\Scripts\Activate.ps1",
        "$PSScriptRoot\..\..\OmniFlowCentral\.venv\Scripts\Activate.ps1",
        ".\.venv\Scripts\Activate.ps1"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) {
            Write-Host "Activating venv: $p"
            . $p
            return $true
        }
    }
    Write-Host "No virtualenv Activate.ps1 found; continuing without activating venv."
    return $false
}

function Start-AzuriteIfRequested {
    param([string]$dbDir = "$PSScriptRoot\..\__azurite_db__")
    if (-not $StartAzurite) { return }
    if (-not (Get-Command azurite -ErrorAction SilentlyContinue)) {
        Write-Host "Azurite not found on PATH; skipping Azurite start." -ForegroundColor Yellow
        return
    }
    if (-not (Test-Path $dbDir)) { New-Item -ItemType Directory -Path $dbDir -Force | Out-Null }
    Write-Host "Starting Azurite (db -> $dbDir)"
    Start-Process -FilePath azurite -ArgumentList "--silent","--location","$dbDir" -NoNewWindow -PassThru | Out-Null
}

function Start-FunctionsHost {
    param([string]$workingDir, [string]$logFile, [int]$port)
    if (-not (Get-Command func -ErrorAction SilentlyContinue)) {
        Write-Error "Azure Functions Core Tools 'func' not found on PATH. Install or add to PATH."
        exit 2
    }

    if (-not (Test-Path $workingDir)) {
        Write-Error "Functions app folder not found: $workingDir"
        exit 2
    }

    Write-Host "Starting Functions host in $workingDir (port $port). Logs -> $logFile"
    $args = "start --port $port"
    $startInfo = @{ FilePath = 'func'; ArgumentList = $args; WorkingDirectory = $workingDir; RedirectStandardOutput = $true; RedirectStandardError = $true; NoNewWindow = $true }
    $proc = Start-Process @startInfo -PassThru

    # redirect output streams to file
    $stdOut = $proc.StandardOutput
    $stdErr = $proc.StandardError
    Start-Job -ScriptBlock {
        param($o, $e, $path)
        while (-not $o.EndOfStream -or -not $e.EndOfStream) {
            try { if (-not $o.EndOfStream) { $line = $o.ReadLine(); Add-Content -Path $path -Value $line } } catch {}
            try { if (-not $e.EndOfStream) { $eline = $e.ReadLine(); Add-Content -Path $path -Value $eline } } catch {}
            Start-Sleep -Milliseconds 50
        }
    } -ArgumentList $stdOut, $stdErr, (Resolve-Path $logFile).Path | Out-Null

    return $proc
}

function Wait-For-Health {
    param([int]$port, [int]$timeoutSec = 60)
    $url = "http://localhost:$port/api/health"
    Write-Host "Waiting for health endpoint: $url"
    $i = 0
    while ($i -lt $timeoutSec) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri $url -Method GET -TimeoutSec 2
            if ($r.StatusCode -eq 200) { Write-Host "health OK"; return $true }
        } catch {}
        Start-Sleep -Seconds 1
        $i++
    }
    Write-Error "Health check did not become healthy in $timeoutSec seconds."
    return $false
}

# --- main
Push-Location $PSScriptRoot
Activate-Venv | Out-Null
Start-AzuriteIfRequested

$functionsDir = Join-Path $PSScriptRoot '..\OmniFlowCentral'
$proc = Start-FunctionsHost -workingDir $functionsDir -logFile $LogFile -port $Port

if ($RunTests) {
    if (Wait-For-Health -port $Port -timeoutSec 60) {
        Write-Host "Running integration tests; output -> tests-integration.log"
        $env:OMNIFLOWCENTRAL_BASE_URL = "http://localhost:$Port"
        Set-Location ".."
        & pytest tests/integration -q 2>&1 | Tee-Object -FilePath tests-integration.log
    } else {
        Write-Error "Skipping tests due to failed health check. See $LogFile for host logs."
    }
}

Write-Host "Functions host started (PID: $($proc.Id)). Tail the log with: Get-Content -Path $LogFile -Wait"
Pop-Location
