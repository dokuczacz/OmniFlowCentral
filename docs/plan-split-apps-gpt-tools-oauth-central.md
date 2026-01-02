# OmniFlow: Split into App1 (Orchestrator) + App2 (GPT Tools + OAuth Central)

Date: 2026-01-02
Owner: Mariusz
Status: Planning (copy/adapt-first; App1 untouched)

---

## 0) Main rule (non‑negotiable)

**Copy and adapt working solutions. Do not refactor App1.**

- App1 remains unchanged (no code moves, no config edits, no route changes).
- App2 is created as a new repo by copying proven code from App1 and adapting only what’s necessary (container name, base URLs, tool surfaces, stricter validation).
- Rollback is always possible by switching the Custom GPT Actions base URL(s) back.

---

## 1) Scope & acceptance criteria

### Goal
Split the current Azure Functions backend into 2 isolated units:

- **App1 Orchestrator**: chat brain + tool loop + WP6/WP7.
- **App2 GPT Tools + OAuth Central**: deterministic blob CRUD tools + OAuth/Gmail/bridge.

### Explicit exclusions from App2 (must NOT be in App2)
- `save_interaction`
- `get_interaction_history`
- `tool_call_handler`
- `wp7_indexer_timer`
- `wp7_indexer_run`
- 'wp6_context_builder'

### Acceptance criteria
- App1 continues to run as-is.
- App2 uses **separate blob containers** and exposes only basic deterministic tools.
- Blob CRUD tool data lives in `omniflowcentralcustomgpt`.
- OAuth/Gmail/bridge live in App2 and use `omniflowcentraloauth`.
- Custom GPT does not do low-level JSON token exchanges; it calls high-level tools.
- Each tool has stable request/response JSON shapes; invalid inputs fail fast with deterministic errors.

---

## 2) Target architecture (contracts)

### App1 — Orchestrator (existing)
- Source: existing repo folder `backend/` (no changes in this phase)
- Owns: LLM runtime loop (`tool_call_handler`), routing,
- Storage: existing container (unchanged) for orchestrator data

### App2 — GPT Tools + OAuth Central (new repo)
- Owns:
  - basic blob tools (blob CRUD primitives)
  - OAuth Central endpoints (`custom_bridge`, `oauth_email`, `gmail_oauth_callback`)
- Storage (same Storage Account):
  - blob tools container: `omniflowcentralcustomgpt`
  - OAuth/Gmail artifacts container: `omniflowcentraloauth`
- Key outputs:
  - Basic tool endpoints (HTTP)
  - `gpt_tools_handler` (HTTP) = single door for GPT (recommended)

---

## 3) What goes where (crucial function inventory)

### App2 — MUST include

Function | Why | Notes
---|---|---
`list_blobs` | GPT needs discovery | enforce namespace + pagination
`read_blob_file` | single read primitive | size limits + safe JSON parse
`read_many_blobs` | batch reads to reduce tool calls | tail support for JSONL/text
`get_filtered_data` | server-side filtering | prevents “read all then filter in model”
`upload_data_or_file` | overwrite/update | validate sizes and content type
`add_new_data` | append record | validate JSON string payload
`update_data_entry` | deterministic edit | strict match rules
`remove_data_entry` | deterministic delete | strict match rules
`manage_files` | rename/delete | keep for admin; optional later
`get_current_time` | debug | optional

### App2 — MUST include (OAuth Central)

Function | Why | Notes
---|---|---
`custom_bridge` | Gmail + GPT integration | centralize all OAuth usage
`oauth_email` | Microsoft OAuth | centralize tokens and refresh
`gmail_oauth_callback` | Gmail OAuth redirect | used by consent flow

### App1 — KEEP only (do not move)

Function | Why
---|---
`tool_call_handler` | orchestration runtime loop (“chat brain”)
`wp7_indexer_timer` | indexing belongs with orchestrator
`wp7_indexer_run` | indexing belongs with orchestrator
`save_interaction` | stays with orchestrator logs (unless later decision)
`get_interaction_history` | stays with orchestrator logs (unless later decision)

Notes:
- App1 also keeps the existing CRUD tool endpoints (blob tools and related HTTP functions). In this split we **do not move** them out of App1; App2 will **duplicate** (copy/adapt) these endpoints for GPT Actions isolation.

---

## 4) Tool handler design (App2) - quasi MCP, copy/adapt-first

### Objective
Make GPT calls robust by hiding messy JSON exchanges and enforcing strict schemas.

### App2 endpoint: `gpt_tools_handler` (preferred)
- Request: `{ "tool": "<name>", "params": { ... }, "user_id": "...", "trace_id": "..." }`
- Response: `{ "status": "success", "result": ... }` or `{ "status": "error", "error": "...", "details": ... }`

Rationale: keep GPT integrations isolated from App1; App1 stays untouched and App2 becomes the single tool surface.

### Routing rules
- For blob tools: call local implementations in App2.
- For oauth/gmail tools: call local OAuth Central functions in App2.

### Non-goals (explicit)
- App2 does **not** implement WP6/WP7 logic (no Context Builder, no semantic conversions, no preferences gating like `_wp6_allowed_to_read`).
- App2 does **not** attempt to cooperate with OpenAI prompts; that remains App1 responsibility.

### Quasi MCP capabilities (recommended)
- `GET /api/capabilities` returns tool list + JSON schemas + examples.
- `POST /api/tools/call` executes a tool with strict validation.

### Params matrix (required)
App2 should keep a single, explicit “params matrix” (tool → required/optional params) as the source of truth for validation.

Existing patterns in App1 (reference only):
- `backend/proxy_router/__init__.py` uses `ACTION_SCHEMA` (action → required keys).
- `backend/tool_call_handler/__init__.py` uses `DATA_EXTRACTION_REQUIRED` (tool → allowed keys) when falling back to proxy dispatch.

App2 recommendation:
- One allow-list dict that drives:
  - strict validation (missing keys → deterministic 4xx)
  - capabilities output (tool list + params)
  - consistent error codes/messages

### Guardrails (do not skip)
- Strict allow-list of tool names.
- Per-tool required parameter validation (fail fast).
- Timeouts + retries for external API calls (OAuth providers, Gmail/Graph).
- Sanitized logging (no tokens/PII in logs).

### Debug central (recommended)
Goal: standardized logs + a single “central point” for error codes/messages.

Current state in App1 (reference):
- `backend/tool_call_handler/__init__.py` has a debug toggle (`DEBUG_TOOL_CALL_HANDLER`/`OMNIFLOW_DEBUG`) and a redaction helper (`_redact_sensitive`), but error codes/messages are not centralized across modules.

App2 recommendation:
- Define a small, explicit error-code registry (e.g., `INVALID_TOOL`, `MISSING_PARAM`, `VALIDATION_FAILED`, `UPSTREAM_TIMEOUT`, `UPSTREAM_ERROR`).
- Emit structured logs with consistent fields (at minimum: `trace_id`, `user_id`, `tool`, `code`, `status`).

---

## 5) Preparation phase (repos) — copy/adapt

### 5.1 Create Repo: `omniflow-gpt-tools` (App2)
- Copy from current working code:
  - blob endpoints and supporting `shared/*` helpers
  - keep behavior stable; tighten validation only
- Copy from App1 (OAuth Central endpoints):
  - `custom_bridge`
  - `oauth_email`
  - `gmail_oauth_callback`
  - required `shared/*` modules (`gmail_*`, `oauth_*`, storage client, config)
- Replace configs:
  - container names (`omniflowcentralcustomgpt`, `omniflowcentraloauth`) (Azure Blob container names must be lowercase)
  - app settings names (App2-specific prefix recommended)

### 5.2 Keep App1 repo unchanged
- App1 stays deployed as-is.

---

## 6) Azure infrastructure phase (via Azure MCP)

> Use Azure MCP tools to create resources. Exact subcommands differ by MCP server; first call each tool with `learn=true` to discover supported commands.

### 6.1 Subscription + resource group
- Choose subscription (MCP): `mcp_azure_mcp_subscription_list`
- Create or select RG (MCP): `mcp_azure_mcp_group_list` (and RG create via CLI/tooling if needed)

Recommended RGs:
- `rg-omniflow-gpt-tools-<region>` (shared by App1 and App2)

### 6.2 Storage containers (same Storage Account)
- Locate storage account (MCP): `mcp_azure_mcp_storage` (learn)
- Create containers:
  - `omniflowcentralcustomgpt`
  - `omniflowcentraloauth`

### 6.3 Function Apps
- Create App2 Function App (MCP): `mcp_azure_mcp_functionapp` (learn)

App1 is not changed in this phase.

### 6.4 Observability
- Create/attach App Insights (MCP): `mcp_azure_mcp_applicationinsights` (learn)
- Optional alerts later (MCP): `mcp_azure_mcp_monitor`

### 6.5 Secrets
Preferred:
- Use Key Vault (MCP): `mcp_azure_mcp_keyvault` (learn)
- Store:
  - OAuth client secrets
  - storage connection string (or use managed identity + RBAC later)

Minimal first iteration:
- Set app settings directly in Function Apps (fast but less secure).

---

## 7) Deployment & cutover (no App1 changes)

### 7.1 Deploy App2
- Deploy independently (CI/CD or manual).

CI/CD (recommended first iteration): GitHub Actions publish-profile deploy
- Workflow file: `.github/workflows/deploy-omniflowcentral.yml`
- Trigger: pushes to `main` when `OmniFlowCentral/**` changes (plus manual `workflow_dispatch`).
- GitHub Secret required:
  - `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` = the full XML from Azure Portal → Function App → **Get publish profile**.
- Azure Portal prerequisite (publish profile auth): ensure SCM basic auth publishing credentials are enabled for the Function App.
- Rollback (deployment): redeploy previous commit or disable the workflow.

### 7.2 Configure Custom GPT Actions
- Preferred “single-door” for GPT:
  - Point GPT tools OpenAPI server URL to App2.
  - Keep App1 out of the tool path (App1 remains unchanged).

### Rollback
- Switch Actions base URL back to previous endpoint(s).

---

## 8) Check/Tests (golden suite)

### App2
- 1 success + 1 failure test per tool:
  - `read_many_blobs`: truncation + tail behavior verified
  - `get_filtered_data`: filter correctness verified
- Validate JSON responses are stable.
- Validate error envelopes + error codes are stable for all validation failures (missing param, invalid tool, invalid types).

### App2 (OAuth Central)
- `oauth_status` before authorization
- `oauth_start` returns URL/state
- `oauth_complete` stores tokens
- `gmail_send` works with stored tokens

### Cross-app
- N/A (App1 is not in the tool path).

---

## 9) Risks & mitigations

Risk | Impact | Mitigation
---|---|---
Custom GPT tool misuse | wrong params / broken flows | strict schemas + handler facade
Token leakage in logs | security | sanitize logs; do not log tokens
Container confusion | data mixing | explicit container per app + env var prefixing
Drift between apps | inconsistent behavior | copy/adapt-first + golden tests

---

## 10) Next decisions (to execute)

1) Region + RG naming convention to use --> use sam RG
1.1) App 2 name: OmniFlowCentral, 2 blob containers: `omniflowcentraloauth`, `omniflowcentralcustomgpt` (Azure Blob container names must be lowercase)
2) Recommended: single-door (GPT calls App2 only).
3) Key Vault now vs later.

---

## 11) Work packages (LEO-friendly batches)

Each implementation step is kept under ~1000 LOC to stay reviewable (lots of copy/adapt). This is what will go into App2.

Work Package | Description | LOC Estimate | Status
---|---|---|---
WP0 – App2 skeleton | Initialize new repo (`host.json`, entrypoints, shared helpers, env var surface) and verify a simple health endpoint | 250–450 | Pending
WP1 – Blob CRUD tools | Copy/adapt list/read/read_many/get_filtered/upload/add/update/remove/manage_files (`omniflowcentralcustomgpt` container) | 700–950 | Pending
WP2 – OAuth Central | Copy/adapt `custom_bridge`, `oauth_email`, `gmail_oauth_callback` + auth storage to `omniflowcentraloauth` | 700–950 | Pending
WP3 – Tool handler + capabilities | Implement `gpt_tools_handler`, `GET /api/capabilities`, tool matrix, error registry | 500–900 | Pending
WP4 – Actions/OpenAPI spec | Produce new OpenAPI pointing at App2, define JSON envelopes, doc new server URL | 250–650 | Pending
WP5 – Golden suite | Smoke script/curl for every tool + error envelope checks + OAuth flows | 300–900 | Pending

---

## 12) Delegation (/delegate) commands (copy/paste)

Use these as CLI `/delegate` prompts to parallelize read-only research before starting implementation. Each delegate must return a self-contained output that can be pasted back into this plan.

### /delegate infra-azure-mcp

Goal: confirm what Azure MCP can do directly (containers, reads) and what must be done via CLI/Portal (Function App creation), and provide an ordered checklist.

```
/delegate infra-azure-mcp
Goal: Produce concrete Azure MCP steps for App2 provisioning (App1 unchanged). Create two blob containers in the SAME Storage Account: `omniflowcentraloauth` and `omniflowcentralcustomgpt`. Use ONE shared resource group for both apps. Constraints: read-only + proposal only; do not edit code; do not deploy. Tasks: (1) discover subcommands for mcp_azure_mcp_storage and mcp_azure_mcp_functionapp using learn=true; (2) propose a minimal sequence of MCP calls (with placeholders) to create/verify containers; (3) document MCP limitations for creating a Function App and the safe fallback (CLI/Portal), plus verification and rollback steps. Output: a short ordered list of MCP calls + required inputs + required permissions.
```

Result (2026-01-02, pasted):

- MCP supports listing subscriptions/RGs and creating blob containers via the `mcp_azure_mcp_storage` tool, but **Function App create is not available** in this MCP surface (read-only `functionapp_get`).
- Minimal MCP checklist (placeholders):
  - `mcp_azure_mcp_subscription_list` -> pick `<SUBSCRIPTION_ID>`
  - `mcp_azure_mcp_group_list` (`subscription=<SUBSCRIPTION_ID>`) -> confirm `<RG_SHARED>`
  - `mcp_azure_mcp_storage storage_account_get` (`subscription=<SUBSCRIPTION_ID>`) -> confirm `<STORAGE_ACCOUNT>`
  - `mcp_azure_mcp_storage storage_blob_container_get` (`account=<STORAGE_ACCOUNT>`, `container=omniflowcentraloauth`) -> create if missing
  - `mcp_azure_mcp_storage storage_blob_container_create` (`account=<STORAGE_ACCOUNT>`, `container=omniflowcentraloauth`)
  - `mcp_azure_mcp_storage storage_blob_container_get` (`account=<STORAGE_ACCOUNT>`, `container=omniflowcentralcustomgpt`) -> create if missing
  - `mcp_azure_mcp_storage storage_blob_container_create` (`account=<STORAGE_ACCOUNT>`, `container=omniflowcentralcustomgpt`)
  - Post-check: list containers with `storage_blob_container_get`.
- Required permissions: at least Storage Blob Data Contributor on the Storage Account (or broader Contributor).
- Fallback (CLI/Portal) needed for Function App creation; use `az storage container create/delete ... --auth-mode login` for verification/rollback of containers.

### /delegate app2-copy-adapt-map (RE-RUN REQUIRED)

Goal: produce the exact copy/adapt checklist (files + env vars) for App2 without importing App1 orchestration code.

```
/delegate app2-copy-adapt-map
Goal: Identify exactly which backend/ folders/files must be copied into the new App2 repo to implement these endpoints: list_blobs, read_blob_file, read_many_blobs, get_filtered_data, upload_data_or_file, add_new_data, update_data_entry, remove_data_entry, manage_files, get_current_time, custom_bridge, oauth_email, gmail_oauth_callback, plus a new gpt_tools_handler and /api/capabilities. Constraints: App1 stays untouched; App2 duplicates behavior. Tasks: (1) for each function folder, list required shared dependencies under backend/shared and backend/tools (imports); (2) list env vars referenced by grepping these modules; (3) flag any coupling to tool_call_handler/wp6/wp7 that must be avoided in App2. Output: a complete markdown table: Function → Required folders/files → Env vars → Notes.
```

Result (2026-01-02): delegate output was incomplete; re-derived below from direct inspection of `backend/` sources.

Copy/adapt map (App2) — concrete checklist

Common dependencies (copy into App2 once):
- `shared/__init__.py`
- `shared/config.py` (defines `AzureConfig`)
- `shared/logging_setup.py` (SDK log control)

Core env vars (App2):
- Storage: `AZURE_STORAGE_CONNECTION_STRING` (or `AzureWebJobsStorage`)
- Tools container: `AZURE_BLOB_CONTAINER_NAME=omniflowcentralcustomgpt`
- Optional logging: `AZURE_SDK_LOG_LEVEL`, `AZURE_HTTP_LOGGING`, `OMNIFLOW_DEBUG`

OAuth/Gmail env vars (App2):
- Microsoft OAuth: `OAUTH_TENANT_ID`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, `OAUTH_REDIRECT_URI`, `OAUTH_SCOPES`, `OAUTH_RESPONSE_MODE`, `OAUTH_PROMPT`
- Gmail OAuth: `GMAIL_OAUTH_CLIENT_ID`, `GMAIL_OAUTH_CLIENT_SECRET`, `GMAIL_OAUTH_REDIRECT_URI`, `GMAIL_OAUTH_SCOPES`, `GMAIL_OAUTH_PROMPT`

IMPORTANT: today the OAuth/Gmail token stores write to `AzureConfig.CONTAINER_NAME` (i.e., `AZURE_BLOB_CONTAINER_NAME`). To satisfy the “2 containers” requirement, WP2 must adapt token stores to use `omniflowcentraloauth` (via a dedicated env var like `AZURE_OAUTH_BLOB_CONTAINER_NAME`, or a separate config class).

Function → Required folders/files → Env vars → Notes

Function | Required folders/files | Env vars | Notes
---|---|---|---
`list_blobs` | `list_blobs/` + common shared deps | Storage + tools container + logging | No coupling to `tool_call_handler`/`wp6`/`wp7`.
`read_blob_file` | `read_blob_file/` + common shared deps | Storage + tools container + logging | Includes basename suffix resolver; keep behavior identical.
`read_many_blobs` | `read_many_blobs/` + common shared deps | Storage + tools container + logging | Uses tail/prefix safety limits.
`get_filtered_data` | `get_filtered_data/` + common shared deps | Storage + tools container + logging | Filters server-side.
`upload_data_or_file` | `upload_data_or_file/` + common shared deps | Storage + tools container + logging | Writes under `users/{user_id}/...`.
`add_new_data` | `add_new_data/` + common shared deps | Storage + tools container + logging | Has stricter validation (path traversal checks).
`update_data_entry` | `update_data_entry/` + common shared deps | Storage + tools container + logging | Deterministic update-on-match.
`remove_data_entry` | `remove_data_entry/` + common shared deps | Storage + tools container + logging | Deterministic delete-on-match.
`manage_files` | `manage_files/` + common shared deps | Storage + tools container + logging | list/delete/rename within user namespace.
`get_current_time` | `get_current_time/` | None | Standalone.
`custom_bridge` | `custom_bridge/` + common shared deps + `shared/gmail_oauth.py` + `shared/gmail_client.py` | Storage + (today) tools container + Gmail OAuth vars | WP2 must move token store to `omniflowcentraloauth`.
`oauth_email` | `oauth_email/` + common shared deps + `shared/oauth_email.py` | Storage + (today) tools container + Microsoft OAuth vars | WP2 must move token store to `omniflowcentraloauth`.
`gmail_oauth_callback` | `gmail_oauth_callback/` + `shared/gmail_oauth.py` (+ common shared deps via import chain) | Storage + (today) tools container + Gmail OAuth vars | Public callback endpoint; stores tokens + deletes state.
`gpt_tools_handler` (new) | New function folder + copy `tools/` (all files) | Depends on which tools are exposed | `tools/*.py` already wraps each function via DummyReq; avoids `tool_call_handler`.
`/api/capabilities` (new) | New function folder | None (if static) | Recommend generating from the allow-list/params matrix used by `gpt_tools_handler`.

Explicitly DO NOT COPY into App2:
- `tool_call_handler/`, `wp7_indexer_timer/`, `wp7_indexer_run/`, `save_interaction/`, `get_interaction_history/`, `proxy_router/`, `shared/wp7_indexer.py`.

### /delegate openapi-actions-schema

Goal: draft the minimal OpenAPI Actions schema for App2 (single-door recommended).

```
/delegate openapi-actions-schema
Goal: Draft a minimal OpenAPI 3.1 Actions schema for App2 exposing (A) POST /api/tools/call and (B) GET /api/capabilities, with strict validation and deterministic error envelopes. Constraints: exclude App1-only endpoints (tool_call_handler, wp7_*, wp6 context builder). Tasks: (1) inspect backend/custom_gpt_tools/actions_openapi.json and derive a minimal subset; (2) propose components/schemas for ToolCallRequest (oneOf with tool enum) and ToolCallResponse (success/error); (3) give a short rationale for single-door vs multi-endpoint. Output: JSON snippets for info/servers/components/paths + rationale.
```

Result (2026-01-02, pasted summary):

- Single-door is recommended: `POST /api/tools/call` + `GET /api/capabilities`.
- Strict JSON schema approach: `tool` allow-list (enum) + per-tool `oneOf` parameter schemas + `additionalProperties: false`.
- Deterministic error envelope recommended for all non-2xx.
- Draft JSON snippets exist (info/servers/components/paths) and will be materialized in WP4 as the App2 Actions/OpenAPI document.
