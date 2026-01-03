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

## OpenAPI (for Custom GPT Actions)

- Single-door spec: `docs/actions_openapi_app2.json`
- Use the raw GitHub URL to that file when importing into GPT Builder (server URL must point to the deployed App2 Function App).

## CI/CD (GitHub Actions)

Workflow: `.github/workflows/deploy-omniflowcentral.yml`

Required secret:
- `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` (download from Azure Portal → Function App → Get publish profile)

## Notes

If tool calls return `Missing AZURE_BLOB_CONTAINER_NAME`, set it in Azure:
- Azure Portal → Function App → Environment variables (Configuration) → add `AZURE_BLOB_CONTAINER_NAME`.
