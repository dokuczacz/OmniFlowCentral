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
- `GET /api/list_blobs`

## CI/CD (GitHub Actions)

Workflow: `.github/workflows/deploy-omniflowcentral.yml`

Required secret:
- `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` (download from Azure Portal → Function App → Get publish profile)

## Notes

If `list_blobs` returns `Missing AZURE_BLOB_CONTAINER_NAME`, set it in Azure:
- Azure Portal → Function App → Environment variables (Configuration) → add `AZURE_BLOB_CONTAINER_NAME`.
