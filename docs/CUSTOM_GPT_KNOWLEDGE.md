# OmniFlow Central - Custom GPT Knowledge (AGENT ONLY)

STRICT RULES:
- Allowed tools: `query_dataset`, `dataset_search`
- Forbidden tools: `read_blob`, `read_many_blobs`, `get_filtered_data`, `eli_acts_query`, any manifest CRUD helpers

CALL SHAPE (REQUIRED):
Always call tools via `/api/tools/gpt/call` using:
```json
{
  "tool": "<query_dataset|dataset_search>",
  "...": "tool fields at root (do NOT wrap in a top-level params object)"
}
```

query_dataset
- `dataset` (required): `eli_acts`
- `q` (optional): string
- `limit` (optional): int (1..100)
- `fetch_content` (optional): bool
- `pageId` (optional): deterministic lookup key
  - `eli_acts`: ELI id like `DU/2025/1882`
- `recordIndex` (optional): deterministic lookup key
  - `eli_acts`: `pos`
- Filters MUST be top-level keys inside `params` (DO NOT send `filters={...}`)
  - `eli_acts`: `year`, `publisher`, `status`

MANDATORY INDEX-FIRST WORKFLOW (lawyer-user):
1) Candidate search (index scan): call `query_dataset` with `fetch_content=false` to get candidates + stable IDs (`pageId`, `recordIndex`) and `provenance.index_path`.
2) Confirm candidate (deterministic): re-call `query_dataset` using `pageId` (and optionally `recordIndex`) instead of relying on `q`.
3) Only after confirmation: use `fetch_content=true`.
   - ELI may return `_fullText` (or `_fullTextTruncated=true` if too large) plus `txt_missing`/`txt_status`.

ELI gotchas (common):
- ELI `pageId` is `DU/<year>/<pos>` (publisher/year/position), e.g. PIT base act is `DU/1991/350` (Dz.U. 1991 nr 80 poz. 350).
- `year=YYYY` filters publication year of the act, not "version in force in YYYY".

Query syntax note:
- The backend supports a minimal boolean subset in `q`: `"A OR B"` or `"A AND B"` (case-insensitive). No parentheses/quotes.
- Prefer setting `fetch_content` explicitly in every call (do not assume a default).

Example (ELI deterministic fetch by ELI id):
```json
{
  "tool": "query_dataset",
  "dataset": "eli_acts",
  "pageId": "DU/2025/1882",
  "fetch_content": false
}
```

dataset_search
- Use only to discover dataset entries in the manifest (category/tags/cursor).
- Recommended:
  - `user_id`: `public`
  - `category`: `dataset`

Example:
```json
{
  "tool": "dataset_search",
  "user_id": "public",
  "category": "dataset",
  "tags_any": ["legal"],
  "limit": 20
}
```

TRUNCATION / SIZE:
- Gateway limit is ~2MB per HTTP response.
- Look for: `truncated=true` and per-hit `_fullTextTruncated=true` / `_fullTextExcerptTruncated=true`.

CITATIONS (REQUIRED IN ANSWERS):
- Always include provenance fields from tool output:
  - `dataset`, `provenance.index_path`, `pageId`, `recordIndex`

## Large-act strategy (2 MB cap)
- The gateway enforces ~2 MB per HTTP response. If you request `fetch_content=true` for a full act like `DU/1997/553`, expect `_fullTextTruncated=true` or a `ResponseTooLargeError`.
- Use optional `params.content_slice` to control the excerpt.
  ```json
  "content_slice": {
    "start": 0,
    "length": 2000
  }
  ```
  - `start` (optional int): byte offset inside `_fullText` (default 0).
  - `length` (optional int): max bytes to return (default 2048, max 4096). The service always obeys the 2 MB hard cap.
- Add `content_slice` only when you already confirmed `pageId` (step 2 above). Keep `limit` small (1-3) to avoid scanning too many hits.
- Responses with `content_slice` include `_fullTextExcerpt` plus `_fullTextTruncated=true` if the native text extends beyond the slice.

## Kodeks karny / large acts fallback runbook
1. `query_dataset` with `dataset="eli_acts"`, `pageId="DU/1997/553"`, `fetch_content=false`, `limit=1` to confirm metadata (no full text).
2. When you need actual provisions, re-call with `fetch_content=true` and `content_slice` covering the article/section you want. Example:
   ```json
   {
     "tool": "query_dataset",
     "dataset": "eli_acts",
     "pageId": "DU/1997/553",
     "fetch_content": true,
     "content_slice": {"start": 0, "length": 4096}
   }
   ```
3. If the gateway rejects the response size, do not retry with the same request. Instead:
   - Keep `content_slice.length` at <= 4096 bytes and move the `start` offset to page through the text safely.
   - Ask the user for the exact article number and narrow the slice to that section (or use multiple slices for adjacent context).
4. Maintain a local mirror for critical acts: upload `users/public/datasets/eli_acts/text/DU/1997/553.txt` so fetches never hit the remote API.
