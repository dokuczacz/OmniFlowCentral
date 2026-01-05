# Environment-to-Config Migration Plan (Milestone B)

## 1. Inventory

- **Beta tool handler (`backend/tool_call_handler/__init__.py`)**
  - Environment-dependent flags currently spread across the top of the module:
    - **Secrets/keys:** `OPENAI_API_KEY`, `ASSISTANT_ID`, `OPENAI_PROMPT_ID`, `OPENAI_VECTOR_STORE_ID`, `PROXY_URL`, `PROXY_FUNCTION_KEY`.
    - **Runtime toggles / feature flags:** `DEBUG_TOOL_CALL_HANDLER`, `OMNIFLOW_DEBUG`, `OMNIFLOW_MOCK_AGENT`, `ENABLE_SAVE_INTERACTION`.
    - **WP6 configuration:** `WP6_DEFAULT_CONTEXT_MODE`, `WP6_RESPONSES_STATELESS`, `WP6_RECENT_TURNS_MAX[_CHARS]`, `WP6_FAST_AUDIT_ENABLED`, `WP6_FAST_AUDIT_MAX_CHARS`, `WP6_AUDIT_DEFAULT_MODEL`, `WP6_AUDIT_DEFAULT_REASONING_EFFORT`, `WP6_FAST_MAX_[INPUT_TOKENS/SOURCES/RAW_BYTES]`, `WP6_DEEP_MAX_PACK_TOKENS`, `WP6_DEEP_MAX_CANDIDATE_SOURCES`, `WP6_DEEP_MIN_SEMANTIC_[SELECTED/CANDIDATES]`, `WP6_CONTEXT_PACK_TTL_SECONDS`, `WP6_DEEP_COOLDOWN_SECONDS`, `WP6_PREFERENCES_AUTO_CREATE`, `WP6_PREFERENCES_TTL_SECONDS`, `WP6_RECENT_TURNS_MAX`, `OPENAI_CONTEXT_BUILDER_PROMPT_ID`.
    - **WP7 configuration:** `WP7_AUDIT_DEFAULT_MODEL`, `WP7_AUDIT_DEFAULT_REASONING_EFFORT`.
    - **Cache / throttling:** `HANDLES_CACHE_TTL_SECONDS`, `PREFERENCES_CACHE_TTL_SECONDS`, `OPENAI_MAX_REQUESTS`.
  - These values are read on module import, making runtime overrides hard to track and duplicating logic elsewhere.

- **Central tool handler (`OmniFlowCentral/shared/config.py`, `local.settings.json`)**
  - Already collects Azure settings via `CONNECTION_STRING`, `CONTAINER_NAME`, `OAUTH_CONTAINER_NAME`.
  - Tracks `OPENAI_API_KEY` and `PROXY_URL`.
  - No WP6/WP7 references yet, and handler-specific defaults live directly in `tools_call/__init__.py`.

## 2. Candidate config entries that can be centralized

| Category | Suggested config key | Current usage |
| --- | --- | --- |
| **Debug/feature flags** | `DEBUG_TOOL_CALL_HANDLER`, `ENABLE_SAVE_INTERACTION`, `OMNIFLOW_DEBUG`, `OMNIFLOW_MOCK_AGENT` | Beta handler toggles; we should expose them via a dataclass so both repos read the same defaults. |
| **WP6 affinity** | `WP6_*` constants listed above | Beta only; central run logic currently bypasses WP6, but config needs to live here once we share the handler dict. |
| **WP7 defaults** | `WP7_AUDIT_DEFAULT_MODEL`, `WP7_AUDIT_DEFAULT_REASONING_EFFORT`, batch/timing thresholds (future) | Used for audit/logging; perfect candidate for a shared `ToolHandlerConfig` object so we can pass the same values to manifests/manifest helper if needed. |
| **Throttles / caches** | `HANDLES_CACHE_TTL_SECONDS`, `PREFERENCES_CACHE_TTL_SECONDS`, `OPENAI_MAX_REQUESTS`, `PROXY_FUNCTION_KEY` | De-duplicated as config constants to avoid naive `os.environ` calls scattered across directories. |
| **Function codes** | `FUNCTION_CODE_*` (listed in `.env.example`) | Currently consumed via direct `os.getenv` in each handler; a config object with defaults and optional overrides would let both projects share invocation metadata. |

## 3. Migration approach (small, reversible steps)

1. **Create a shared `ToolHandlerConfig` dataclass/module** (e.g., `OmniFlowCentral/shared/tool_handler_config.py`):
   - Reads env vars once and exposes typed attributes with clear defaults (string, bool, int).
   - Validates any required secrets (e.g., `OPENAI_API_KEY`) while leaving optional toggles flexible.
   - Document the fallback values so operators understand what is configurable.

2. **Phase B1 (next coding step)**: migrate the WP7 constants into `ToolHandlerConfig`:
   - Move `WP7_AUDIT_DEFAULT_MODEL` and `WP7_AUDIT_DEFAULT_REASONING_EFFORT` into the config object.
   - Have `backend/tool_call_handler/__init__.py` and `OmniFlowCentral/tools_call/__init__.py` import the config object and use `config.WP7_AUDIT_DEFAULT_MODEL` rather than reading env internally.
   - Add a new unit test to ensure the config uses the expected default values and can be overridden via environment.
   - This keeps the change contained to a few files, satisfying the “pure Python tool handler 1” principle and allowing us to verify via targeted tests.

3. **Phase B2 (follow-up)**: extend the config object to additional categories (debug toggles, WP6 settings, cache TTLs, function codes) in subsequent mini batches.
   - Each batch should include updating both central and beta handlers, verifying there is no runtime difference.
   - Where configuration parameters are only relevant to Beta (e.g., `WP6_FAST_AUDIT_ENABLED`), keep them in Beta but derived from the shared config value to avoid divergence.

4. **Validation / regression guard**:
   - Unit tests for `ToolHandlerConfig` should cover default values, boolean parsing, and float/int conversion where applicable.
   - Document how to override values locally (CI/local settings) so the shared config remains readable.

5. **Next actions (Milestone B deliverable)**:
   - Implement Phase B1 (WP7 constants) and verify Beta, Central, and shared manifest helpers still behave the same.
   - Update relevant README or docs to describe the new config module and list the env vars it centralizes.

6. **Documentation alignment**
   - Added a note to `docs/shared/ENVIRONMENT_VARIABLES.md` (Beta) pointing to `backend/shared/tool_handler_config.py` as the consumer of all WP6/WP7 entries.
   - Keep this plan updated as new envs are centralized so the documentation mirrors the code.

_This file records Milestone B’s scope and ensures each config migration stays small, repeatable, and testable._
