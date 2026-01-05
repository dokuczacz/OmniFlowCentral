# Tool Handler Comparison and Next Improvements

## Scope, Inputs/Outputs, Acceptance Criteria
- **Scope:** document the current architecture of the Beta (`backend/tool_call_handler`) and Central (`tools_call`) tool handlers, note strengths/weaknesses, and record concrete improvement ideas for Central ahead of the pure-Python refactor.
- **Inputs:** source code in `OmniFlowBeta/backend/tool_call_handler/__init__.py` and `OmniFlowCentral/tools_call/__init__.py`, plus shared helpers imported by each.
- **Outputs:** this comparison document and a list of prioritized improvements/config targets that can stay in the repo until the refactor is broken into small steps.
- **Acceptance:** the document captures the analysis requested (logic level, good/weak points, unification goals) and lists at least the top 3 improvement actions plus config migration candidates for Central.

## Beta tool handler (`backend/tool_call_handler/__init__.py`)
- **Purpose:** orchestrates OpenAI runs (FAST/DEEP/AUTO) with WP6/WP7 routing, preferences, run polling, and tool execution. It is the heavyweight entrypoint for the assistant’s runtime.
- **Logic level:** very advanced. Handles preferences caching, WP6 gating (_wp6_allowed_to_read_), WP7 audit logging, context pack reuse, run creation/polling, and fallbacks for in-progress runs. It also wraps HTTP tools such as `restore_session` and `read_blob_file` via `_inprocess_*` helpers to avoid network latency when possible.
- **Strengths:**
  - Deep integration with WP6/7, including policy enforcement, audit logging, and throttles per environment variables near the top of the file (e.g., `WP6_FAST_MAX_INPUT_TOKENS`, `WP7_AUDIT_DEFAULT_MODEL`).
  - Smart caching (`_handles_cache`, `_prefs_cache`) and synchronous in-process calls that eliminate extra HTTP round trips for internal helpers.
  - Centralized `_best_effort_debug`, `_make_response`, and `_emit_run_progress` ensure consistent telemetry despite the handler’s complexity.
- **Weaknesses / risks:**
  - Extremely long, monolithic file (~40K LOC) makes targeted changes error prone and hard to review.
  - Heavy reliance on environment variables scattered across the top of the file complicates reasoning about defaults (many `os.environ.get(...)` calls before any config abstraction).
  - Because of the bespoke WP6/7 logic, porting simple CRUD tools into this handler introduces a lot of unrelated context and state.

## Central tool handler (`tools_call/__init__.py`)
- **Purpose:** exposes simpler blob/dataset tools for centralized automation workflows. Focus is on raw storage ops rather than managing runs.
- **Logic level:** pragmatic and concise. Each handler is a one-function wrapper around `shared.blob_ops` or `shared.data_ops`, parameter parsing helpers (`_as_int`, `_require_param`, `_as_bool`), and validation plus `TOOL_SPECS` enforcement.
- **Strengths:**
  - Clear, test-friendly layout where each HTTP tool maps directly to a dedicated helper function (`_handle_list_blobs`, `_handle_upload`, etc.).
  - Reuses shared helpers for alias resolution (`canonical_tool_name`, `apply_param_aliases`) so tooling contracts are consistent.
  - Error payloads built via `shared.error_codes`, matching the established schema (`status`, `code`, `trace_id`) the front end expects.
- **Weaknesses / improvement areas:**
  - Tools like `upload_blob`/`read_blob` still call out to individual functions; there’s no shared dict for constructing CRUD handlers step-by-step (unlike Beta’s `_inprocess_*` helpers).
  - No centralized config object; defaults and toggles are embedded in the handler rather than versioned/shared configs (contrast `backend/shared/config.py` in Beta).
  - Latency could be reduced by rolling `add_new_data`/`remove_data_entry` into the handler’s dict so that no HTTP layer is involved for these smaller helpers.

## Improvement notes for Central (actionable items)
1. **Dict-driven handler registry:** derive the per-tool logic from a shared dictionary that can gradually expand to include `manage_files`, CRUD data helpers, and eventual WP6 gating helpers. This is the “dict step-by-step” you mentioned.
2. **Pure-Python operations:** keep core handlers (list, read, upload, dataset CRUD) in-process without HTTP proxies—already true for most operations, but extend to any new helpers (e.g., `upload_data_or_file`, `manage_files`) before wiring them through the orchestrator.
3. **Config consolidation:** consolidate environment variables (starting with the ones referenced in `shared.config` and those in `.env.example`) into a versioned config object shared by Central and Beta tool handlers. Candidates include WP7 batch sizes/timeouts, handler feature flags (`ENABLE_SAVE_INTERACTION`, `OMNIFLOW_DEBUG`), and function codes.
4. **Manifest & interaction parity:** now that manifest helper and interaction logging are aligned with Beta, ensure the planned manifest-writing steps are included in the doc (done elsewhere). This doc can link to `backend/shared/manifest_helper.py` and to the new `interactions/index.jsonl` approach.
5. **Testing/validation:** as we roll in new helpers (e.g., `get_filtered_data`, `dataset_search`), update tests alongside each function to keep the dict reference consistent. Since we’re working in small batches, each new helper should have an automated coverage check before moving on.

## Next steps (small, reversible actions)
1. Record the env-to-config candidates and decide which subset we can migrate as a single step (soon-to-be part of config migration plan).
2. Build the shared dict for tool handlers: start with `TOOL_HANDLERS`, then backfill missing helpers by copying logic from the explicit `_handle_*` functions.
3. Align `shared/manage_files_params` logic between Beta and Central so both handlers can share the same alias/validation helpers the new dict will rely on.

## Beta agent cleanup instructions
Use this checklist when trimming Beta's handler surface:
1. **Whitelist the helpers** - accept only `add_new_data`, `get_current_time`, `get_filtered_data`, `list_blobs`, `read_blob_file`, `read_many_blobs`, `remove_data_entry`, `update_data_entry`, `upload_data_or_file`, and `manage_files`. Any other `action` should return `403` with "allowed_actions".
2. **Remove redundant endpoints** - delete/archive `save_interaction`, `get_interaction_history`, `proxy_router`, `tool_call_handler`, `wp6_*`, `wp7_*`, etc., from the public handler, leaving internal helper modules only for direct executables.
3. **Update documentation** - call out the narrowed Beta surface in this doc/runbooks and explain that the helper modules live under `tools/` and are invoked via the whitelist.
4. **Sweep for stale usage** - search tests/scripts for the removed action names and convert them to the allowable helpers or remove them so the handler's behavior matches the whitelist.

Document updated: recorded per-request improvement points for Central; see this file for next refactor discussions._
