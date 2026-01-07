# Query Dataset Tool - Unified Search with Content Fetching

## Overview
`query_dataset` is a unified tool that replaces dataset-specific query handlers (like `eli_acts_query`) with a single, flexible interface. It supports:

- **Multiple datasets** (ELI acts, SAOS judgments, future datasets)
- **Text search** across relevant fields
- **Dataset-specific filters** (year, publisher, court, etc.)
- **Optional full content fetching** in a single API call

## Why This Approach?

Instead of calling separate tools:
1. Query index → get IDs
2. Call `read_blob` for each ID → get full content

You can now do both in one call:
```json
{
  "tool": "query_dataset",
  "dataset": "saos_judgments",
  "q": "Amber Gold",
  "limit": 5,
  "fetch_content": true
}
```

This solves the `ResponseTooLargeError` problem because:
- Index search is fast and returns only matching IDs
- Full content is fetched only for matches (not entire page files)
- Results are batched and controlled by `limit`

## Supported Datasets

### `eli_acts`
Polish legislative acts from Sejm ELI API.

**Filters:**
- `q`: text search in title
- `year`: publication year
- `publisher`: publisher name (e.g., "DU", "MZ")
- `status`: status filter (e.g., "obowiązujący")
- `limit`: max results (1-100, default 10)

**Example:**
```json
{
  "tool": "query_dataset",
  "dataset": "eli_acts",
  "q": "Prawo budowlane",
  "year": 2025,
  "limit": 5
}
```

### `saos_judgments`
Polish court judgments from SAOS API.

**Filters:**
- `q`: text search in summary, caseNumber, court
- `court`: court name filter (e.g., "Gdańsk")
- `court_type`: court type (e.g., "COMMON", "APPEAL")
- `limit`: max results (1-100, default 10)
- `fetch_content`: if `true`, returns full judgment details

**Example:**
```json
{
  "tool": "query_dataset",
  "dataset": "saos_judgments",
  "q": "Amber Gold",
  "court": "Gdańsk",
  "limit": 10,
  "fetch_content": true
}
```

## Response Format

```json
{
  "status": "success",
  "dataset": "saos_judgments",
  "total_scanned": 20000,
  "total_returned": 3,
  "limit": 10,
  "fetch_content": true,
  "truncated": true,
  "warning": "Response truncated to soft cap.",
  "hits": [
    {
      "caseNumber": "II K 38/16",
      "court": "Sąd Okręgowy w Gdańsku",
      "courtType": "COMMON",
      "judgmentDate": "2017-05-15",
      "summary": "Amber Gold - oszustwo...",
      "pageId": "page_00042",
      "recordIndex": 17,
      "_contentTruncated": true,
      "_fullContent": {
        // Full judgment object if fetch_content=true
      }
    }
  ],
  "provenance": {
    "index_path": "datasets/saos/judgments/index/judgments_index.jsonl"
  }
}
```

Notes:
- When full content exceeds the per-item soft cap, `_contentTruncated: true` is returned and `_fullContent` is omitted.
- When the overall response exceeds the soft cap, `truncated: true` and a `warning` are included, and results may be shortened.

## Building Indexes

### SAOS Index
```bash
python scripts/saos_build_index.py --max-pages 10 --write-index
```

This reads `datasets/saos/judgments/pages/page_*.json` and creates `datasets/saos/judgments/index/judgments_index.jsonl`.

### ELI Index
Already built via `eli_dump_to_blob.py`:
```bash
python scripts/eli_dump_to_blob.py --max-pages 5 --write-index-jsonl
```

## Backward Compatibility

`eli_acts_query` is still supported but internally delegates to `query_dataset` with `dataset="eli_acts"`.

## Adding New Datasets

1. Build NDJSON index at `datasets/{name}/index/{name}_index.jsonl`
2. Add entry to `DATASET_INDEX_REGISTRY` in `shared/data_ops.py`
3. Add filtering logic to `_matches_filters()` and `_text_search_match()`
4. Optionally add content fetching logic to `_attach_full_content()`
5. Update OpenAPI schema and tool specs

## Usage in Custom GPT

Custom GPT can now:
- Search datasets without worrying about file sizes
- Get full content in one call when needed
- Use simpler prompts: "Find Amber Gold cases in SAOS" → calls `query_dataset` with `fetch_content=true`
