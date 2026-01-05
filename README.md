# OmniFlowCentral

Azure Functions (Python) backend dedicated to Custom GPT tools + OAuth artifacts.

## What this repo is

This repo is intentionally narrow:
- Deploys only the Azure Functions app located in `OmniFlowCentral/`.
- Keeps tool endpoints and OAuth-related storage isolated from the legacy app (App1).

## Azure resources (expected)

- Function App name: `OmniFlowCentral`
- Blob containers (lowercase):
  - `omniflowcentralcustomgpt` (tool data)
  - `omniflowcentraloauth` (OAuth artifacts)

## Local development

Prereqs:
- Python 3.11
- Azure Functions Core Tools

Environment:
- `AzureWebJobsStorage` (Azurite or real storage)
- `AZURE_BLOB_CONTAINER_NAME=omniflowcentralcustomgpt`

Run:
- `cd OmniFlowCentral`
- `pip install -r requirements.txt`
- `func start`

## Deployed endpoints

Both HTTP triggers are `authLevel: function`.

- `GET /api/health`
- `POST /api/tools/call` (single-door GPT tools handler)
- `GET /api/tools/capabilities` (tool list + params)
- `POST /api/custom_bridge` (Gmail bridge + OAuth + send/list/get/attach)
- `GET|POST /api/oauth_email` (Microsoft OAuth token management for GPT email)
- `GET /api/gmail_oauth_callback` (OAuth redirect for Google consent)

### Available Tools

Standard CRUD tools:
- `list_blobs`, `upload_blob`, `delete_blob`, `read_blob`, `read_many_blobs`
- `get_filtered_data`, `upload_data_or_file`, `add_new_data`, `update_data_entry`, `remove_data_entry`
- `manage_files`, `dataset_search`

Public datasets:
- `eli_acts_query` - Query Polish legislative acts from Sejm ELI API (59,000 records)
  - Filters: `q` (title search), `year`, `publisher`, `status`, `limit`
  - See [`docs/ELI_INTEGRATION_SUMMARY.md`](docs/ELI_INTEGRATION_SUMMARY.md) for details

## OpenAPI (for Custom GPT Actions)

- Single-door spec: `docs/actions_openapi_app2.json`
- Use the raw GitHub URL to that file when importing into GPT Builder (server URL must point to the deployed App2 Function App).

## Data import (ELI / Sejm)

Script: `scripts/eli_dump_to_blob.py`

Example (quick try: few pages to Azurite; uploads to storage configured via env vars):

```powershell
$env:AzureWebJobsStorage = "UseDevelopmentStorage=true"
$env:AZURE_BLOB_CONTAINER_NAME = "omniflowcentralcustomgpt"

python .\\scripts\\eli_dump_to_blob.py --max-pages 3 --write-index-jsonl
```

To export the stored pages into one JSONL file for indexing:

```powershell
$env:AzureWebJobsStorage = "UseDevelopmentStorage=true"
$env:AZURE_BLOB_CONTAINER_NAME = "omniflowcentralcustomgpt"

python .\\scripts\\eli_index_export.py --output data/eli_acts_index.jsonl
```

After exporting, you can inspect `docs/eli_acts_data_export.md` for a Markdown summary of the converted dataset (sample rows, run metadata, storage layout).

## CI/CD (GitHub Actions)

Workflow: `.github/workflows/deploy-omniflowcentral.yml`

Required secret:
- `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` (download from Azure Portal → Function App → Get publish profile)

## Notes

If tool calls return `Missing AZURE_BLOB_CONTAINER_NAME`, set it in Azure:
- Azure Portal → Function App → Environment variables (Configuration) → add `AZURE_BLOB_CONTAINER_NAME`.
