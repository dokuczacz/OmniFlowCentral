# Query Dataset — Minimal Contract (ELI + SAOS)

`query_dataset` is the single supported tool for searching and reading **public** datasets stored in blob storage.

## Public Storage Paths (Source of Truth)
All dataset paths referenced by `query_dataset` are under:
- `users/public/datasets/eli_acts/...`
- `users/public/datasets/saos/...`

If you see `datasets/...` examples (without `users/public/...`), treat them as historic.

## Request Shape (Always)
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "eli_acts | saos_judgments",
    "q": "<optional search text>",
    "pageId": "<optional deterministic id>",
    "recordIndex": "<optional deterministic index>",
    "limit": 10,
    "fetch_content": false
  }
}
```

## Mandatory Workflow (Scan → Confirm → Fetch)
To avoid false negatives and “fragile” title matches, always do:
1) **Scan:** use `q=...` with `fetch_content=false` to get candidate IDs.
2) **Confirm:** re-call using `pageId` (and `recordIndex` when applicable).
3) **Fetch:** only after confirmation, set `fetch_content=true` (keep `limit` small).

## Response Size Rules (Important)
The API enforces:
- a **global response soft cap** (if exceeded: `truncated: true`, `warning: ...`, hits may be shortened),
- a **per-item content cap** (if exceeded: content is omitted and a `*_Truncated` flag is returned).

Treat any `*_Truncated=true` as “content exists but was not inlined”.

---

## Dataset: `eli_acts` (ELI / Dz.U. / M.P.)

### IDs and filters (common pitfall)
- `pageId` format is `DU/<year>/<pos>` or `MP/<year>/<pos>` (publisher + year + position).
  - Example PIT base act: `DU/1991/350` (Dz.U. 1991 nr 80 poz. 350 → `pos=350`).
- `year` filter is **publication year of the act**, not “version in force in that year”.
  - Example: filtering `year=2025` will not find PIT base act from 1991.
- Text search (`q`) is a literal substring match (no stemming). Prefer:
  - shorter keyword queries, and/or
  - deterministic lookups by `pageId`.

### Content fetching (`fetch_content=true`)
When enabled, backend tries to attach:
- `_fullText` (from `users/public/datasets/eli_acts/text/<ELI>.txt`),
- or `_fullTextTruncated: true` if too large,
- and always reports: `txt_missing` + `txt_status` (`ok` / `skipped`).

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

**C) Fetch content for a confirmed act (small `limit`)**
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "eli_acts",
    "pageId": "DU/2026/17",
    "fetch_content": true,
    "limit": 1
  }
}
```

---

## Dataset: `saos_judgments` (SAOS)

### Current search scope (why “0 results” happens)
Text search (`q`) currently matches mainly in:
- `summary`
- `caseNumber`
- `court`

If a legal concept is not present in those fields, `total_returned=0` is expected.

### Deterministic IDs
- `pageId` is the page blob id (e.g. `page_00042`).
- `recordIndex` is the item index within the JSON array stored in that page.

### Content fetching (`fetch_content=true`)
When enabled, backend tries to attach `_fullContent` (single judgment object). If too large:
- `_contentTruncated: true` is returned and `_fullContent` is omitted.

### Minimal examples
**A) Scan by phrase**
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "saos_judgments",
    "q": "klauzule abuzywne",
    "limit": 10,
    "fetch_content": false
  }
}
```

**B) Confirm + fetch (small `limit`)**
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "saos_judgments",
    "pageId": "page_00042",
    "recordIndex": 17,
    "fetch_content": true,
    "limit": 1
  }
}
```

---

## Interpreting `status=success` + `total_returned=0`
This means the query executed correctly, but nothing matched.
Before concluding “no data”, check (in order):
1) remove restrictive filters (`year`, `court`, etc.),
2) shorten `q` (no stemming; avoid long exact titles),
3) use deterministic `pageId` with correct `DU/<year>/<pos>` / `MP/<year>/<pos>` format,
4) keep `limit` small when `fetch_content=true`.

## Common aliases (operator guidance)
To reduce false negatives in natural language prompts, normalize these in your query wording:
- “Dz.U.” ↔ `DU`
- “dz ust” ↔ `DU`
- “M.P.” / “Monitor Polski” ↔ `MP`
- “poz.” ↔ `pos` (but prefer `pageId` when you know it)
