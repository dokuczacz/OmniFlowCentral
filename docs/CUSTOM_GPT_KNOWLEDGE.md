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
- `params.pageId` (optional): deterministic lookup key
  - `eli_acts`: ELI id like `DU/2025/1882`
  - `saos_judgments`: page id like `page_00001`
- `params.recordIndex` (optional): deterministic lookup key
  - `eli_acts`: `pos`
  - `saos_judgments`: index within page array (requires `pageId`)
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

MANDATORY INDEX-FIRST WORKFLOW (lawyer-user):
1) Candidate search (index scan): call `query_dataset` with `fetch_content=false` to get candidates + stable IDs (`pageId`, `recordIndex`) and `provenance.index_path`.
2) Confirm candidate (deterministic): re-call `query_dataset` using `pageId` (and optionally `recordIndex`) instead of relying on `q`.
3) Only after confirmation: use `fetch_content=true` (SAOS returns `_fullContent`; ELI currently returns metadata only).

Query syntax note:
- The backend supports a minimal boolean subset in `q`: `"A OR B"` or `"A AND B"` (case-insensitive). No parentheses/quotes.
- Prefer setting `fetch_content` explicitly in every call (do not assume a default).

Example (ELI deterministic fetch by ELI id):
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "eli_acts",
    "pageId": "DU/2025/1882",
    "fetch_content": false
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
