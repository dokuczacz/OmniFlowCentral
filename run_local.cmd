@echo off
setlocal
cd /d "%~dp0"

REM Double-click entrypoint for Windows (App2).
REM Creates venv + installs deps + runs Azurite + Azure Functions host.

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3.11 scripts\run_local.py
  goto :done
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python scripts\run_local.py
  goto :done
)

echo ERROR: Neither "py" nor "python" found on PATH.
pause
exit /b 1

:done
endlocal
