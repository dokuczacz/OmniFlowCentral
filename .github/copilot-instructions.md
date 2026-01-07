
### Process rules live in .github/instructions/…; this file is repo context only.

### Purpose
Provide quick, actionable guidance for AI coding agents working in this repository so they become productive immediately.

Assumptions
- You're running from the repository root.
- Local dev uses Azurite for blob storage and the Azure Functions Core Tools or the provided `scripts/run_local.py` wrapper.

Top-level architecture (big picture)
- Python Azure Functions app located in `OmniFlowCentral/` exposing HTTP routes under `api/` (e.g. `/api/tools/call`, `/api/tools/capabilities`, `/api/health`).
- Core shared logic lives in `OmniFlowCentral/shared/`:
  - `blob_ops.py` — low-level Azure blob helpers and naming conventions (`users/{user_id}/...`).
  - `manifest_helper.py` — manifest read/write at `manifests/{user}/manifest.json` used by `dataset_search`.
  - `data_ops.py` — higher-level operations (upload, list, `dataset_search`, new `eli_acts_query`).
  - `tool_specs.py` and `tool_catalog.py` — canonical tool capability definitions consumed by `tools_capabilities`.
- Request dispatch: `OmniFlowCentral/tools_call/__init__.py` maps `tool` names to handler functions. Handlers return structured JSON via `shared/response.py` helpers.
- Data flow example: `dataset_search` reads `manifests/{user}/manifest.json` → finds `blob_name` → `eli_acts_query` reads `users/public/datasets/eli_acts/index/acts_inforce_1.jsonl` via `blob_ops`.

Key developer workflows & commands
- Run full app locally (recommended): start Azurite + Functions host or use the provided helper:
  - `python scripts/run_local.py` (wraps Functions host + environment)
- Run only the in-process handler tests (no Functions host):
  - `python scripts/test_eli_http_endpoint.py` (imports handlers directly using `MockHttpRequest`)
- Build/update ELI dataset index and upload pages to blob:
  - `python scripts/eli_dump_to_blob.py --max-pages <N> --write-index-jsonl`
  - Or build index from already-uploaded pages: `--build-index-from-blob --write-index-jsonl`
- Inspect/verify manifest operations: `scripts/register_eli_dataset.py`, `scripts/verify_manifest_ops.py`.

Packaging & deployment notes
- Azure Functions deployment installs `OmniFlowCentral/requirements.txt`. To ensure the package is importable on the host we add a repo-level `setup.py` and an editable install entry (`-e ..`) inside `OmniFlowCentral/requirements.txt`. Confirm pipeline runs `pip install -r OmniFlowCentral/requirements.txt` during deployment.
- Do not commit secrets. Function keys and storage connection strings must be supplied via environment variables or `local.settings.json` (not committed). Example env keys: `OMNIFLOW_CAP_URL`, `OMNIFLOW_CALL_URL`, `AzureWebJobsStorage`.

Project-specific conventions and patterns
- Blob names are namespaced per user: functions use helper `_apply_user_prefix(name, user_id)` or `users/{user_id}/...` literals for public data. Keep this pattern when adding new storage artifacts.
- Manifest entry shape and location: `manifests/{user}/manifest.json` — use `manifest_helper.build_manifest_entry()` and `upsert_manifest_entry()` to keep manifests consistent.
- Tool discovery: `shared/tool_specs.py` defines `TOOL_SPECS` (name, method, params). Keep new tools registered there so `tools_capabilities` exposes them.
- Handler registration: add handler function in `OmniFlowCentral/tools_call/__init__.py` and map the tool name in `TOOL_HANDLERS` to enable `/api/tools/call` dispatch.
- Tests: many tests call handlers in-process by inserting repo root into `sys.path`. Avoid relying on editable installs when writing tests intended to simulate Azure environment — prefer spinning up Functions host + Azurite for integration-level checks.

Integration points & external dependencies
- Azure Blob Storage (local: Azurite). Key config: `AzureConfig.CONTAINER_NAME` and `AzureConfig.CONNECTION_STRING` in `OmniFlowCentral/shared/config.py` and `local.settings.json`.
- Azure Functions Python worker — function bindings declared in each function folder's `function.json`.
- External API: Sejm ELI API used by `scripts/eli_dump_to_blob.py` (ELI_BASE_URL).

Troubleshooting checklist (common causes of failures)
- ModuleNotFoundError on Azure: ensure package is installed by `pip install -r OmniFlowCentral/requirements.txt` and that `setup.py` exists at repo root (or use `git+https` requirement). See `OmniFlowCentral/requirements.txt` for `-e ..` usage.
- 500 / empty body from Azure: inspect Function App logs (Kudu / Azure Portal) for import errors and confirm `pip install` output.
- Missing dataset blobs: `eli_acts_query` raises NOT_FOUND if `users/public/datasets/eli_acts/index/acts_inforce_1.jsonl` is missing — run `scripts/eli_dump_to_blob.py --write-index-jsonl` to populate.

What to avoid (project-specific)
- Do not commit function keys or other secrets into scripts — use environment variables. Example: `scripts/call_remote_tools.py` must read keys from env.
- Avoid large single commits touching many function folders; prefer small, targeted patches (this repo treats function directories as independent units).

Files to inspect first (fast onboarding)
- `OmniFlowCentral/shared/blob_ops.py` — storage helpers and naming conventions.
- `OmniFlowCentral/shared/data_ops.py` — tool implementations and dataset_search/eli_acts_query.
- `OmniFlowCentral/tools_call/__init__.py` — HTTP entry and dispatch mapping.
- `OmniFlowCentral/tools_capabilities/__init__.py` — capability exposure (reads `TOOL_SPECS`).
- `scripts/eli_dump_to_blob.py` and `scripts/register_eli_dataset.py` — dataset ingestion + manifest registration examples.
- `scripts/run_local.py` — local run wrapper.

If you change code, minimal checklist before committing
1. Update `shared/tool_specs.py` when adding tools.
2. Register handler in `OmniFlowCentral/tools_call/__init__.py`.
3. Run `python scripts/test_eli_http_endpoint.py` for in-process sanity or `python scripts/run_local.py` + HTTP call for integration.
4. Don’t commit secrets; use env vars.

Feedback
If any section is unclear or you'd like more examples (e.g., exact handler skeleton or a sample `requirements.txt` snippet), tell me which area to expand.
