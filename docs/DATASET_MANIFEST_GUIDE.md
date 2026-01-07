# Dataset Manifest and Exploration Guide

## Overview

The dataset manifest is a JSON file that enables dataset discovery through the `dataset_search` tool. It's stored in blob storage at `manifests/{user}/manifest.json` and indexes all available datasets for that user.

## Current Status (as of 2026-01-07)

### ELI Acts Dataset
- **Status:** ✅ Deployed and operational
- **Location:** `users/public/datasets/eli_acts/index/acts_inforce_1.jsonl`
- **Records:** ~59,000 Polish legislative acts
- **Tool:** `query_dataset` (recommended) or `eli_acts_query` (legacy)
- **Manifest:** Needs to be added to `manifests/public/manifest.json`

### SAOS Judgments Dataset  
- **Status:** ⏳ In progress
- **Location:** TBD (`users/public/datasets/saos/` planned)
- **Tool:** `query_dataset` (will use same unified interface)
- **Manifest:** To be added after dataset creation

## Recommended Tool: query_dataset

**Always use `query_dataset` with `fetch_content=true` for best performance:**

### Why query_dataset?
1. **Single call** - Get full records without additional fetches
2. **Unified interface** - Same tool for all datasets (ELI, SAOS, future additions)
3. **Better limits** - Built-in safety caps and chunking
4. **Future-proof** - Designed for expansion

### Example Usage

**Discover datasets:**
```json
{
  "tool": "dataset_search",
  "payload": {
    "user_id": "public",
    "params": {
      "category": "dataset"
    }
  }
}
```

**Query with content (recommended):**
```json
{
  "tool": "query_dataset",
  "payload": {
    "params": {
      "dataset": "eli_acts",
      "q": "podatek",
      "year": 2025,
      "limit": 10,
      "fetch_content": true
    }
  }
}
```

## Manifest Structure

### public/manifest.json (target structure)

```json
{
  "manifest_version": 1,
  "updated_at": "2026-01-07T16:00:00Z",
  "entries": [
    {
      "blob_name": "datasets/eli_acts/index/acts_inforce_1.jsonl",
      "display_name": "ELI Legislative Acts (Sejm)",
      "summary": "Polish legislative acts dataset from Sejm ELI API - acts with inForce=1 status",
      "tags": ["eli", "legislation", "sejm", "poland", "legal"],
      "category": "dataset",
      "source": "https://api.sejm.gov.pl/eli/acts/search",
      "size": 89596000,
      "content_type": "application/x-ndjson",
      "updated_at": "2026-01-06T10:00:00Z",
      "created_at": "2026-01-05T12:00:00Z",
      "metadata": {
        "tool": "query_dataset",
        "dataset_name": "eli_acts",
        "record_count": 59000,
        "format": "ndjson",
        "fields": ["ELI", "title", "publisher", "year", "status", "displayAddress"],
        "filters": ["q", "year", "publisher", "status"]
      }
    },
    {
      "blob_name": "datasets/saos/index/judgments_index.jsonl",
      "display_name": "SAOS Court Judgments",
      "summary": "Polish court judgments from Supreme Administrative Court (SAOS)",
      "tags": ["saos", "judgments", "court", "poland", "legal"],
      "category": "dataset",
      "source": "https://www.saos.org.pl",
      "size": 0,
      "content_type": "application/x-ndjson",
      "updated_at": "2026-01-07T16:00:00Z",
      "created_at": "2026-01-07T16:00:00Z",
      "metadata": {
        "tool": "query_dataset",
        "dataset_name": "saos_judgments",
        "record_count": 0,
        "format": "ndjson",
        "per_record_storage": true,
        "fields": ["judgment_id", "court_type", "judgment_date", "case_number"],
        "filters": ["court_type", "year", "case_number"]
      }
    }
  ]
}
```

## How to Update the Manifest

### Option 1: Use script (recommended)

```bash
python scripts/register_eli_dataset.py
```

This will:
1. Connect to Azure blob storage
2. Get ELI index metadata
3. Build manifest entry
4. Upload to `manifests/public/manifest.json`

### Option 2: Manual via blob_ops

```python
from OmniFlowCentral.shared.manifest_helper import upsert_manifest_entry

entry = {
    "blob_name": "datasets/eli_acts/index/acts_inforce_1.jsonl",
    "display_name": "ELI Legislative Acts (Sejm)",
    "summary": "Polish legislative acts dataset from Sejm ELI API - acts with inForce=1 status",
    "tags": ["eli", "legislation", "sejm", "poland", "legal"],
    "category": "dataset",
    "metadata": {
        "tool": "query_dataset",
        "dataset_name": "eli_acts",
        "record_count": 59000
    }
}

upsert_manifest_entry(user_id="public", entry=entry)
```

## Custom GPT Instructions (Updated)

Add this to your Custom GPT instructions:

```
# Dataset Querying (Legal Research)

When asked about Polish legislation or court judgments:

1. **Use query_dataset tool with fetch_content=true** (single call, best performance)
   - For legislation: {"dataset": "eli_acts", "q": "<search>", "fetch_content": true}
   - For court judgments: {"dataset": "saos_judgments", "q": "<search>", "fetch_content": true}

2. **Legacy fallback:** eli_acts_query (deprecated, use query_dataset instead)

3. **Discovery:** Use dataset_search to find available datasets
   - {"user_id": "public", "tags_any": ["legal"]}

Always cite sources with ELI/SAOS identifiers and official references.
```

## Performance Notes

### Safety Limits
`query_dataset` enforces the per-response soft cap (~2MB) and sets `truncated: true` when it had to drop hits, while `_contentTruncated` flags the individual records whose content was not included. Let the API trim automatically rather than trying to stream raw JSON pages yourself.

### Best Practices
1. Always call `query_dataset` with `fetch_content=true` when you need full records.
2. Narrow the search with filters (year, court, status, tags) before raising the limit.
3. Handle `truncated` / `_contentTruncated` in the assistant’s logic as a signal to explain potential missing content.

## Next Steps

1. ✅ **Complete:** Blob operations limits and chunking
2. ✅ **Complete:** query_dataset with fetch_content
3. ⏳ **Pending:** Update public manifest with ELI dataset entry
4. ⏳ **Pending:** Create SAOS per-judgment dataset structure
5. ⏳ **Pending:** Build SAOS index and add to manifest
6. ⏳ **Pending:** Update Custom GPT prompts with new guidance

## References

- Implementation: [`docs/IMPLEMENTATION_QUERY_DATASET.md`](IMPLEMENTATION_QUERY_DATASET.md)
- ELI usage: [`docs/ELI_USAGE_GUIDE.md`](ELI_USAGE_GUIDE.md)
- Query dataset: [`docs/QUERY_DATASET.md`](QUERY_DATASET.md)
- Blob operations: [`OmniFlowCentral/shared/blob_ops.py`](../OmniFlowCentral/shared/blob_ops.py)
