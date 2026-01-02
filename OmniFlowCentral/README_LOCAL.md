# Running OmniFlowCentral locally

Quick steps to run the Functions host and integration smoke tests locally (Windows).

1) Create and activate a Python 3.11 venv (recommended):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r OmniFlowCentral/requirements.txt
```

2) Start the Functions host (in a new PowerShell window, or run in current shell):

```powershell
# from repo root
python .\scripts\run_local.py
# or with tests after host is healthy
python .\scripts\run_local.py --run-tests
```

3) Logs:
- Functions host logs: `logs/omniflowcentral-func-*.log`
- Integration pytest output: `logs/tests-integration.log`

If you prefer manual steps, change directory to `OmniFlowCentral` and run `func start`.
