# Tool Handler Refactor Notes (Central vs Beta)

Date: 2026-01-04
Repo: `OmniFlowCentralRepo` (Central/App2) + comparison with `OmniFlowBeta` (Beta/App1)

## Scope

This note captures:
- improvement points for Central tool handler (`OmniFlowCentral/tools_call/__init__.py`) and adjacent contracts,
- a purpose-aware comparison with Beta orchestrator handler (`OmniFlowBeta/backend/tool_call_handler/__init__.py`),
- GitHub issue drafts for tracking.

## Acceptance Criteria (for refactor readiness)

Central handler is considered “refactor-ready” when:
- request contract and param validation are explicit and enforced (not only described),
- error codes/statuses are consistent across all tools,
- tool parameter naming is stable and harmonized (aliases are intentional and documented),
- observability fields (`trace_id`, `user_id`, `tool`, `code`, `status`) are consistent across success/error logs,
- behavior remains deterministic (caps/timeouts enforced server-side; no orchestration logic leaks in).

## Code Level Evaluation (maturity, purpose-fit)

### Central (App2 / deterministic GPT tools gateway)

Primary entrypoint:
- `OmniFlowCentral/tools_call/__init__.py` (`main`, `TOOL_HANDLERS`, `_error_response`, `_success_response`)

Assessment:
- Maturity: **mid** for a deterministic gateway (good scaffolding: allow-list + envelope + shared error registry).
- Purpose-fit: **high** (keeps orchestration out; focuses on deterministic storage/search tools).
- Refactor risk: **low–medium** (small surface, but contract details need hardening).

### Beta (App1 / orchestrator + tool loop)

Primary entrypoint:
- `OmniFlowBeta/backend/tool_call_handler/__init__.py` (`main`, `execute_tool_call`, WP6 routing + persistence)

Assessment:
- Maturity: **high** for orchestration features (routing AUTO/FAST/DEEP, caching, preferences gating, multiple fallbacks).
- Purpose-fit: **high** for App1 (tool loop + runtime control), **low** as a public “tool gateway”.
- Refactor risk: **high** (monolith ~3900 LOC with mixed concerns; higher chance of regression from changes).

## Central Improvements (weak points to address)

### 1) Enforce request contract + schema validation (not only descriptions)

Current:
- `OmniFlowCentral/shared/tool_specs.py` is descriptive metadata only.
- `OmniFlowCentral/tools_call/__init__.py` validates only a subset via per-tool handlers and helper functions.

Improve:
- Introduce a per-tool validation layer driven by a single “params matrix” (required/optional keys, type expectations, aliasing rules, `additionalProperties=false` semantics).
- Ensure all tools reject unknown top-level keys in `params` (or intentionally ignore with an explicit allowlist).

### 2) Fix/standardize parameter naming and aliasing

Current example:
- `_handle_get_filtered_data` accepts `target_blob_name` or `blob_name` or `file_name` (implicit aliasing).
- Other tools accept multiple legacy keys (`file_name` vs `target_blob_name`).

Improve:
- Define canonical param names per tool.
- Define explicit aliases (mapping table) and deprecate legacy keys with deterministic warnings in logs.

### 3) Make error codes/statuses consistent across modules

Current:
- `OmniFlowCentral/shared/error_codes.py` defines a registry, but internal code uses additional codes (e.g., `NOT_FOUND` in data ops) and sometimes returns `MISSING_PARAM` for “not found”.

Improve:
- Add missing standard codes to registry (at least `NOT_FOUND`, `UPSTREAM_TIMEOUT`, `RATE_LIMITED` if used).
- Ensure “not found” is always `NOT_FOUND` + 404 across tools.
- Ensure validation errors are always `VALIDATION_FAILED` + 400.

### 4) Request parsing: stop silently dropping query params (or document it)

Current:
- `OmniFlowCentral/shared/request_contract.py` only uses query params for `tool`, then sets payload to JSON body.

Improve:
- Either merge `req.params` into payload (with precedence rules), or explicitly document “body-only params”.

### 5) Observability hardening (minimal, consistent fields)

Current:
- `trace_id` is passed through if present, but logging is not structured consistently.

Improve:
- Standardize logs for every request: `trace_id`, `user_id`, `tool`, `status`, `code`, `duration_ms`.
- Ensure sensitive payload redaction strategy exists before OAuth tools are added (tokens/PII).

### 6) Tighten user identity handling for public exposure

Current:
- `_resolve_user_id` falls back to `"default"` and accepts `payload.user_id` if header/query absent.

Improve:
- Decide policy for App2: either require header user_id (fail fast) or accept body user_id only from trusted callers (e.g., internal API key).
- Document the policy in capabilities/README to avoid accidental multi-tenant mixing.

## GitHub Issue Drafts (copy/paste)

Repo remote: `https://github.com/dokuczacz/OmniFlowCentral.git`

1) Title: Enforce tool params matrix + strict validation in `tools_call`
   - Scope: `OmniFlowCentral/tools_call/__init__.py`, `OmniFlowCentral/shared/tool_specs.py`
   - AC: unknown params rejected; required params enforced; aliases explicit.

2) Title: Standardize error codes (`NOT_FOUND`, timeouts) and fix inconsistent 404 handling
   - Scope: `OmniFlowCentral/shared/error_codes.py`, `OmniFlowCentral/shared/blob_ops.py`, `OmniFlowCentral/shared/data_ops.py`
   - AC: 404 always uses `NOT_FOUND`; registry contains all used codes.

3) Title: Clarify/merge request contract (`req.params` vs JSON body) for tool calls
   - Scope: `OmniFlowCentral/shared/request_contract.py`
   - AC: documented precedence and consistent behavior across local/integration tests.

4) Title: Add structured logging fields for tools_call (trace_id/user_id/tool/duration)
   - Scope: `OmniFlowCentral/tools_call/__init__.py`
   - AC: logs include standard fields; redaction strategy defined.

5) Title: Decide and enforce `user_id` policy for App2 (header-required vs trusted-body)
   - Scope: `OmniFlowCentral/shared/user_validator.py`, `OmniFlowCentral/tools_call/__init__.py`
   - AC: deterministic behavior; no accidental default-tenant mixing.

