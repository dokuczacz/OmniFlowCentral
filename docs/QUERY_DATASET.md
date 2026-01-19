# Query Dataset — Minimal Contract (ELI)

`query_dataset` is the single supported tool for searching and reading **public** datasets stored in blob storage.

## Public Storage Paths (Source of Truth)
All dataset paths referenced by `query_dataset` (for PrawoL) are under:
- `users/public/datasets/eli_acts/...`

If you see `datasets/...` examples (without `users/public/...`), treat them as historic.

## Request Shape (Always)
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "eli_acts",
    "q": "<optional search text>",
    "pageId": "<optional deterministic id>",
    "recordIndex": "<optional deterministic index>",
    "limit": 10,
    "fetch_content": false,
    "content_slice": {"start": 0, "length": 2048}
  }
}
```

## Mandatory Workflow (Scan → Confirm → Fetch)
To avoid false negatives and fragile title matches, always do:
1) **Scan:** use `q=...` with `fetch_content=false` to get candidate IDs.
2) **Confirm:** re-call using `pageId` (and `recordIndex` when applicable).
3) **Fetch:** only after confirmation, set `fetch_content=true` and use `content_slice` for bounded excerpts.

## Response Size Rules (Important)
The gateway enforces ~2 MB per HTTP response. Treat any `*_Truncated=true` as "content exists but was not inlined".

---

## Dataset: `eli_acts` (ELI / Dz.U. / M.P.)

### IDs and filters (common pitfall)
- `pageId` format is `DU/<year>/<pos>` or `MP/<year>/<pos>` (publisher + year + position).
  - Example PIT base act: `DU/1991/350` (Dz.U. 1991 nr 80 poz. 350 — `pos=350`).
- `year` filter is **publication year of the act**, not "version in force in that year".
- Text search (`q`) is a literal substring match (no stemming). Prefer:
  - shorter keyword queries, and/or
  - deterministic lookups by `pageId`.

### Content fetching (`fetch_content=true`)
When enabled, backend tries to attach:
- `_fullText` for small documents,
- `_fullTextExcerpt` when `content_slice` is provided (recommended),
- `_fullTextTruncated: true` if the full text is too large,
- and reports: `txt_missing` + `txt_status` (`ok` / `skipped`).

### Minimal examples
**A) Scan by topic (no content)**
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "eli_acts",
    "q": "podatek dochodowy",
    "limit": 10,
    "fetch_content": false
  }
}
```

**B) Confirm deterministically by `pageId` (metadata only)**
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "eli_acts",
    "pageId": "DU/1991/350",
    "fetch_content": false,
    "limit": 1
  }
}
```

**C) Fetch bounded excerpt for a confirmed act**
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "eli_acts",
    "pageId": "DU/1997/553",
    "fetch_content": true,
    "limit": 1,
    "content_slice": {"start": 0, "length": 4096}
  }
}
```

---

## Interpreting `status=success` + `total_returned=0`
This means the query executed correctly, but nothing matched.
Before concluding "no data", check (in order):
1) shorten `q` (no stemming; avoid long exact titles),
2) use deterministic `pageId` with correct `DU/<year>/<pos>` / `MP/<year>/<pos>` format,
3) remove restrictive filters (`year`, `publisher`, `status`),
4) keep `limit` small when `fetch_content=true`.

## Common aliases (operator guidance)
To reduce false negatives in natural language prompts, normalize these in your query wording:
- "Dz.U." → `DU`
- "dz ust" → `DU`
- "M.P." / "Monitor Polski" → `MP`
- "poz." → `pos` (but prefer `pageId` when you know it)
