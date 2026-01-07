# Running OmniFlowCentral locally

Quick steps to run the Functions host and integration smoke tests locally (Windows).

1) Create and activate a Python 3.11 venv (recommended):

```powershell
cd "C:\AI memory\NewHope\OmniFlowCentralRepo"
# If you previously created `.venv` with a different Python (e.g. 3.13), delete it first
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r OmniFlowCentral/requirements.txt
```

If you forget to rebuild `.venv` after switching Python versions, the inline helper (`scripts/run-local.py`) now detects the mismatch, deletes the old environment, and recreates it with Python 3.11 before installing requirements.

2) Start the Functions host (use whichever helper fits your workflow):

- Use `scripts/run_local.py` to spawn the host, Azurite (if configured), and the Next.js chatbot each in their own window. The existing helper already assumes the `.venv` has been created during step 1.
- Alternatively, run the new inline helper that is written in Python and mirrors the former `scripts/run-local.ps1`:

```powershell
# creates .venv + installs requirements if needed, starts the host, and writes the host log to logs/omniflowcentral-run.log
python .\scripts\run-local.py --start-azurite
# run tests after the host goes healthy
python .\scripts\run-local.py --start-azurite --run-tests
```

Pass `--skip-install` to `scripts/run-local.py` if you already created `.venv` manually and only want to start the runtime/test infrastructure.

3) Logs:
- Functions host logs: `logs/omniflowcentral-func-*.log`
- Integration pytest output: `logs/tests-integration.log`

- Inline helper (run-local.py) host log: `logs/omniflowcentral-run.log`
- Inline helper tests log: `tests-integration.log`

If you prefer manual steps, change directory to `OmniFlowCentral` and run `func start`.

## local.settings.json
`OmniFlowCentral/local.settings.json` is intentionally not tracked (contains secrets). Create it by copying:

```powershell
Copy-Item OmniFlowCentral/local.settings.template.json OmniFlowCentral/local.settings.json
```

Then fill required `GMAIL_OAUTH_*` and storage settings for local runs.

## Default user override

- Set environment variable `OMNIFLOW_DEFAULT_USER_ID` to force a default user_id used by handlers
	when no header/query/body user is provided. Example (PowerShell):
	- `$env:OMNIFLOW_DEFAULT_USER_ID = "default"`
	- This affects endpoints like `/api/tools/call` and `/api/read_blob_file`.

## Public → default migration

- A helper script copies blobs from `users/public/` to `users/default/`:
	- Dry run: `python scripts/migrate_public_to_default.py`
	- Execute: `python scripts/migrate_public_to_default.py --apply`
	- Include datasets: add `--include-datasets`
	- Delete sources after copy: add `--delete-source`
	- Overwrite existing targets: add `--overwrite`
