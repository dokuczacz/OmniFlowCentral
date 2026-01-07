# OmniFlow Central – Dataset Discovery Guide

## Problem
Listing all blobs in the container (9000+) times out. **Solution**: Use **blob prefix queries** to access specific datasets.

## Available Datasets

### 1. ELI (European Legal Information) – Polish Acts

#### Metadata (6 files)
**Path prefix**: `datasets/eli/metadata/`

Files available:
- `institutions.json` - Court and institution definitions
- `keywords.json` - Act keywords index (~70KB)
- `publishers.json` - Publisher registry
- `references.json` - Cross-reference metadata
- `statuses.json` - Act status codes
- `types.json` - Act type classifications
- `download_summary.json` - Metadata download run info

**Query example**:
```
GET /api/list_blobs?prefix=datasets/eli/metadata&max_results=10
```

#### Acts Pages (Full Acts Data - 159 pages)
**Path prefix**: `datasets/eli_acts/pages/`

Pages: `acts_offset_000000000.json` → `acts_offset_000078500.json`
Each ~400-900 KB JSON with 500 acts per file.

**Query example**:
```
POST /api/tools/call
{
  "tool": "read_many_blobs",
  "params": {
    "files": [
      "datasets/eli_acts/pages/acts_offset_000000000.json",
      "datasets/eli_acts/pages/acts_offset_000000500.json"
    ]
  }
}
```

#### Acts Index (JSONL - Queryable)
**Direct file**: `datasets/eli_acts/index/acts_inforce_1.jsonl`
- 40,000+ acts indexed as newline-delimited JSON
- **Recommended**: Use `query_dataset` with `fetch_content=true` for single-call queries

**Query example (recommended - unified tool):**
```json
POST /api/tools/call
{
  "tool": "query_dataset",
  "params": {
    "dataset": "eli_acts",
    "q": "finansowanie społecznościowe",
    "limit": 10,
    "fetch_content": true
  }
}
```

**Legacy alternative:**
```json
POST /api/tools/call
{
  "tool": "eli_acts_query",
  "params": {
    "q": "finansowanie społecznościowe",
    "limit": 10
  }
}
```
> Note: `eli_acts_query` is deprecated. Use `query_dataset` for better performance.

### 2. SAOS (Supreme Court) – Judgments Database

#### Judgments Pages (200 pages migrated)
**Path prefix**: `datasets/saos/judgments/pages/`

Pages available: `page_00000.json` → `page_00199.json`
Each ~1.6-2.2 MB JSON with 100 judgments per page.
**Total**: 200 pages = 20,000 judgments (~400 MB)

**Query example**:
```
GET /api/list_blobs?prefix=datasets/saos/judgments/pages&max_results=10
```

**Read example**:
```json
POST /api/tools/call
{
  "tool": "read_blob",
  "params": {
    "name": "datasets/saos/judgments/pages/page_00000.json"
  }
}
```
> Note: Single files are capped at 500KB. For larger files, use chunking or query_dataset.

#### Judgments Index
**Status**: ✅ **Index ready!**
**Direct file**: `datasets/saos/judgments/index/judgments_index.jsonl`
- **20,000 judgments** indexed as newline-delimited JSON (338.1 MB)
- Searchable with future `saos_judgments_query` tool
- Built: 2026-01-07

**Metadata**: `datasets/saos/judgments/metadata/index_summary.json`
Query index (recommended - uses query_dataset):**
```json
POST /api/tools/call
{
  "tool": "query_dataset",
  "params": {
    "dataset": "saos_judgments",
    "q": "Amber Gold",
    "court": "Gdańsk",
    "limit": 10,
    "fetch_content": true
  }
}
```

**Direct read (for inspection only):**
```json
POST /api/tools/call
{
  "tool": "read_blob",
  "params": {
    "name": "datasets/saos/judgments/index/judgments_index.jsonl"
  }
}
```
> Warning: This file is 338MB. Direct read will be truncated at 500KB soft cap. Use query_dataset instead.
```

#### SAOS Metadata (Legacy - Common Courts)
**Path prefix**: `datasets/saos/commonCourts/`

**Note**: Old dataset structure - replaced by judgments/ structure above.

### 3. SAOS (Supreme Court) – Common Courts (Legacy)

#### Common Courts Pages
**Path prefix**: `datasets/saos/commonCourts/pages/`

Pages available: `page_00000.json` → `page_00003.json`
Each ~30-80 KB JSON.

**Query example**:
```
GET /api/list_blobs?prefix=datasets/saos/commonCourts/pages
```

#### SAOS Metadata
**Path prefix**: `datasets/saos/commonCourts/metadata/`

Files: `download_summary.json` with run info.

---

## Usage Patterns

### Pattern 1: List dataset files
```http
GET /api/list_blobs?prefix=datasets/eli/metadata&timeout_seconds=30
```
Query datasets (recommended)
```json
POST /api/tools/call
{
  "tool": "query_dataset",
  "params": {
    "dataset": "eli_acts",
    "q": "konsorcjum",
    "year": 2020,
    "limit": 20,
    "fetch_content": true
  }
}
```
> Use `query_dataset` with `fetch_content=true` to get complete records in one call. "parse_json": true
  }
}
```

### Pattern 3: Search acts
```json
POST /api/tools/call
{
  "tool": "eli_acts_query",
  "params": {
    "q": "konsorcjum",
    "year_from": 2020,
    "limit": 20
  }
}
```

### Pattern 4: Filter dataset entries
```json
POST /api/tools/call
{
  "tool": "get_filtered_data",
  "params": {
    "target_blob_name": "datasets/eli/metadata/types.json",
    "filter_key": "active",
    "filter_value": true
  }
}
```

---
Use query_dataset with fetch_content=true** – Best performance, single call for data + content
2. **Always use prefixes** with `/api/list_blobs` to avoid timeout
3. **SAOS expansion** complete – 20K judgments indexed and ready
4. **ELI full coverage** – 40K+ acts already indexed and searchable
5. **Safety limits** – read_blob: 500KB cap, read_many: 1.25MB total, chunking available
6. **No user prefix needed** – blobs are stored directly under `datasets/`
3. **ELI full coverage** – 40K+ acts already indexed and searchable
4. **No user prefix needed** – blobs are stored directly under `datasets/`
5. **Timeout settings** – use `timeout_seconds=30` for prefix queries to be safe

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 400 Bad Request | Listing too many blobs at once | Add `prefix` to narrow scope |
| 404 Not Found | Wrong blob path | Use `/api/list_blobs?prefix=datasets/eli/metadata` to find actual names |
| Empty result | Prefix too specific | Try broader prefix like `datasets/` |
| Timeout | Full container list attempted | Always specify `prefix` parameter |

