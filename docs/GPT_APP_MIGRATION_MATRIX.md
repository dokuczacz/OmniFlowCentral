# GPT App Migration Matrix (PrawoL -> MCP App)

## Scope

This matrix tracks migration from Custom GPT `PrawoL` (OpenAPI actions) to GPT App (Apps SDK + MCP) for OmniFlowCentral.

## AS-IS -> TO-BE

| Existing Tool | MCP Tool Name | Phase | Status | Notes |
|---|---|---|---|---|
| `query_dataset` | `query_dataset` | phase-1 | implemented | Core PrawoL retrieval path. |
| `dataset_search` | `dataset_search` | phase-1 | implemented | Dataset discovery parity. |
| `eli_acts_query` | `eli_acts_query` | phase-2 | planned | Deprecated backend tool; keep for compatibility only if required. |
| `search` (new) | `search` | phase-1.5 | implemented | MCP/company-knowledge-compatible wrapper over `query_dataset`. |
| `fetch` (new) | `fetch` | phase-1.5 | implemented | MCP/company-knowledge-compatible wrapper for deterministic fetch. |
| `list_blobs` | `list_blobs` | phase-3 | planned | Read-only namespace ops after auth hardening. |
| `read_blob` | `read_blob` | phase-3 | planned | Read file payloads after auth hardening. |
| `read_many_blobs` | `read_many_blobs` | phase-3 | planned | Potentially expensive; stricter limits required. |
| `get_filtered_data` | `get_filtered_data` | phase-3 | planned | Read-only extraction with rate limits. |
| `upload_blob` | `upload_blob` | phase-4 | deferred | Write action; OAuth + confirmation required. |
| `delete_blob` | `delete_blob` | phase-4 | deferred | Destructive action; elevated safeguards required. |
| `upload_data_or_file` | `upload_data_or_file` | phase-4 | deferred | Write action; OAuth + audit logging required. |
| `add_new_data` | `add_new_data` | phase-4 | deferred | Write action; OAuth + confirmation required. |
| `update_data_entry` | `update_data_entry` | phase-4 | deferred | Write action; OAuth + confirmation required. |
| `remove_data_entry` | `remove_data_entry` | phase-4 | deferred | Destructive write; elevated safeguards required. |
| `manage_files` | `manage_files` | phase-4 | deferred | Mixed write/destructive operations; post-MVP scope. |

## Initial Implementation Delivered

- New MCP package: `OmniFlowCentral/mcp_app/`
- Implemented tools:
  - `query_dataset`
  - `dataset_search`
  - `search` (compatibility wrapper)
  - `fetch` (compatibility wrapper)
  - `migration_matrix` (operational visibility)

## Local Run

1. Install MCP dependencies:
   - `pip install -r OmniFlowCentral/requirements-mcp.txt`
2. Start MCP server:
   - `python scripts/run_mcp_server.py`
3. Connect MCP client to:
   - `http://127.0.0.1:8000/mcp`

## Integration Test Gate (Required After Every WU)

After **every** working unit (WU), run the integration gate before marking the unit complete.

1. Run MCP in-memory golden suite (WP2):
   - `python scripts/wp2_mcp_golden_suite.py`
2. Run targeted MCP/unit checks:
   - `python -m pytest tests/unit/test_tools_call.py tests/unit/test_query_dataset_lookup.py tests/unit/test_mcp_contract_search_fetch.py -q`
3. Preferred one-command gate:
   - `python scripts/run_wu_integration_gate.py`

If either command fails, the WU is not complete and must be fixed before proceeding.
