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
- `POST /api/tools/call` (unified tools dispatcher; preferred entrypoint)
- `GET /api/tools/capabilities` (tool list + params; diagnostics)
- `POST /api/custom_bridge` (Gmail bridge + OAuth + send/list/get/attach)
- `GET|POST /api/oauth_email` (Microsoft OAuth token management for GPT email)
- `GET /api/gmail_oauth_callback` (OAuth redirect for Google consent)

### Available Tools

Primary dataset tool:
- `query_dataset` (unified): `eli_acts`
  - Contract + examples: `docs/QUERY_DATASET.md`

Discovery tool:
- `dataset_search` (manifest discovery / dataset listing)

## OpenAPI (for Custom GPT Actions)

- Tools contract: `docs/openapi_tools_call.yaml`

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

After exporting, use `docs/QUERY_DATASET.md` for the current query contract and examples.

## CI/CD (GitHub Actions)

Workflow: `.github/workflows/deploy-omniflowcentral.yml`

Required secret:
- `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` (download from Azure Portal → Function App → Get publish profile)

## Notes

If tool calls return `Missing AZURE_BLOB_CONTAINER_NAME`, set it in Azure:
- Azure Portal → Function App → Environment variables (Configuration) → add `AZURE_BLOB_CONTAINER_NAME`.
