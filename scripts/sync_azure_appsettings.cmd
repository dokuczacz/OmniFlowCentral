@echo off
setlocal
REM Usage:
REM   scripts\sync_azure_appsettings.cmd <ResourceGroup> [FunctionAppName]
REM Example:
REM   scripts\sync_azure_appsettings.cmd AgentResourceGroup OmniFlowCentral

set RG=%1
set APP=%2

if "%RG%"=="" (
  echo ERROR: Missing ResourceGroup.
  echo Usage: %~nx0 ^<ResourceGroup^> [FunctionAppName]
  exit /b 1
)

if "%APP%"=="" (
  set APP=OmniFlowCentral
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync_azure_appsettings.ps1" -ResourceGroup "%RG%" -FunctionAppName "%APP%"
exit /b %ERRORLEVEL%

