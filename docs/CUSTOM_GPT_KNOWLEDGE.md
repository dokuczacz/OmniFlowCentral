# OmniFlow Central - Custom GPT Knowledge (AGENT ONLY)

STRICT RULES:
- Allowed tools: `query_dataset`, `dataset_search`
- Forbidden tools: `read_blob`, `read_many_blobs`, `get_filtered_data`, `eli_acts_query`, any manifest CRUD helpers

CALL SHAPE (REQUIRED):
Always call tools via `/api/tools/call` using:
```json
{
  "tool": "<query_dataset|dataset_search>",
  "params": { }
}
```

query_dataset
- `params.dataset` (required): `eli_acts` | `saos_judgments`
- `params.q` (optional): string
- `params.limit` (optional): int (1..100)
- `params.fetch_content` (optional): bool
- Filters MUST be top-level keys inside `params` (DO NOT send `filters={...}`)
  - `eli_acts`: `year`, `publisher`, `status`
  - `saos_judgments`: `court`, `court_type`

Example (SAOS):
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "saos_judgments",
    "q": "Amber Gold",
    "limit": 5,
    "fetch_content": true,
    "court_type": "common"
  }
}
```

dataset_search
- Use only to discover dataset entries in the manifest (category/tags/cursor).
- Recommended:
  - `params.user_id`: `public`
  - `params.category`: `dataset`

Example:
```json
{
  "tool": "dataset_search",
  "params": {
    "user_id": "public",
    "category": "dataset",
    "tags_any": ["legal"],
    "limit": 20
  }
}
```

TRUNCATION / SIZE:
- Responses may be truncated around ~2MB.
- Look for: `truncated=true` and per-hit `_contentTruncated=true`.

CITATIONS (REQUIRED IN ANSWERS):
- Always include provenance fields from tool output:
  - `dataset`, `provenance.index_path`, `pageId`, `recordIndex`
