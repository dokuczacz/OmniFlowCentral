# Implementation Summary: Unified query_dataset Tool

## ✅ Completed (2026-01-07)

### 1. SAOS Index Builder
**File:** `scripts/saos_build_index.py`
- Reads `datasets/saos/judgments/pages/page_*.json` (large JSON arrays)
- Extracts individual judgment records
- Writes NDJSON index to `datasets/saos/judgments/index/judgments_index.jsonl`
- Each line is a searchable judgment with: caseNumber, court, summary, keywords, etc.

**Usage:**
```bash
python scripts/saos_build_index.py --max-pages 10 --write-index
```

### 2. Unified query_dataset Backend
**Files:** 
- `OmniFlowCentral/shared/data_ops.py`
- `OmniFlowCentral/shared/tool_specs.py`
- `OmniFlowCentral/tools_call/__init__.py`

**Features:**
- Single tool for all dataset queries
- Dataset registry: `eli_acts`, `saos_judgments` (extensible)
- Dataset-specific filters (year, publisher, court, court_type, etc.)
- **fetch_content option**: fetch full blob content for matches in one call
- Backward compatible: `eli_acts_query` delegates to `query_dataset`

**Key Functions:**
- `query_dataset()` - main entry point
- `_matches_filters()` - dataset-specific filtering
- `_text_search_match()` - text search across relevant fields
- `_attach_full_content()` - optional content fetching for matched records

### 3. OpenAPI Schema Update
**File:** `docs/openapi_tools_call.yaml`
- Added `query_dataset` to tool enum
- Added parameters: `dataset`, `fetch_content`, `court`, `court_type`
- Added examples for ELI and SAOS queries with content fetching
- Validated with `openapi_spec_validator` → OK

### 4. Documentation
**File:** `docs/QUERY_DATASET.md`
- Usage guide for Custom GPT and API clients
- Dataset registry and filter documentation
- Response format examples
- How to add new datasets

## Problem Solved

### Before
❌ **Two-step process:**
1. Query index → get IDs/blob names
2. Use `query_dataset` to fetch full content directly; it avoids `ResponseTooLargeError` by honoring the soft cap and returning `truncated` metadata when results were trimmed.

❌ **get_filtered_data on page files:**
- Loads entire 100-judgment JSON array
- Filters in memory → still too large for response

### After
✅ **Single query_dataset call:**
```json
{
  "tool": "query_dataset",
  "dataset": "saos_judgments",
  "q": "Amber Gold",
  "court": "Gdańsk",
  "limit": 5,
  "fetch_content": true
}
```
- Searches lightweight NDJSON index (one line per judgment)
- Returns only matching records
- Optionally fetches full content only for matches
- No ResponseTooLargeError because limit controls batch size

## Custom GPT Benefits

1. **Single-call search + fetch**: no need to chain tools
2. **Safe pagination**: `limit` param prevents oversized responses
3. **Smart content loading**: only fetch details when needed
4. **Extensible**: future datasets (e.g., court_acts, regulations) just add to registry

## Next Steps (Optional)

1. **Build SAOS index**: run `saos_build_index.py --write-index` to populate index
2. **Deploy to Azure**: push updated code to Function App
3. **Test in Custom GPT**: 
   - Search ELI: `{"tool":"query_dataset","dataset":"eli_acts","q":"Prawo budowlane","limit":3}`
   - Search SAOS with content: `{"tool":"query_dataset","dataset":"saos_judgments","q":"Amber Gold","fetch_content":true,"limit":5}`
4. **Register SAOS in manifest**: add dataset entry to manifests/public/manifest.json

## Commit
- **SHA:** 727b29a
- **Branch:** main
- **Status:** Pushed to origin/main
- **Validation:** OpenAPI schema OK, backward compatibility preserved

## DoD Status
✅ Custom GPT has unified tool for search + fetch
✅ No more ResponseTooLargeError from large page files
✅ Backward compatible (eli_acts_query still works)
✅ Documented and validated
✅ Committed and pushed to GitHub

## Ops Plan (2026-01-11)

### Goal: both datasets usable in Azure

**SAOS (mirror → switch registry)**
1. Mirror blobs: `datasets/saos/...` → `users/public/datasets/saos/...` (so Custom GPT can read public namespace).
2. After mirror is verified, switch `DATASET_INDEX_REGISTRY["saos_judgments"]` to point at `users/public/datasets/saos/...` (keep the old path temporarily for rollback).
3. Re-run quick E2E: `query_dataset(dataset="saos_judgments")` and `fetch_content=true` on a few samples.

**ELI (complete PDF→TXT on Azure)**
1. Continue seeding missing `.txt` blobs under `users/public/datasets/eli_acts/text/<ELI>.txt`.
2. For oversized texts: implement a chunking strategy to avoid response caps while keeping index stable.

### Tool Capabilities (planned)
- Add a lightweight guidance overlay (non-breaking) so clients can discover tools and also retrieve best-practice prompting hints without mixing it into the param schema. Prefer a separate tool or a top-level `guidance` field in `/tools/capabilities`.
