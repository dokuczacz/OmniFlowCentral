# Custom GPT Knowledge Base - Recommended Files

## Priority Files (Must Have)

These files should be attached to your Custom GPT's knowledge base for optimal performance:

### 1. **openapi_tools_call.yaml** ⭐ CRITICAL
- **Purpose:** Complete API schema with all tools, parameters, and examples
- **Why:** Custom GPT uses this for tool discovery and correct parameter formatting
- **Status:** ✅ Updated with query_dataset recommendations
- **Path:** `docs/openapi_tools_call.yaml`

### 2. **DATASET_MANIFEST_GUIDE.md** ⭐ CRITICAL
- **Purpose:** Dataset discovery, manifest structure, and best practices
- **Why:** Shows how to use query_dataset with fetch_content, safety limits
- **Key info:** 
  - Unified query_dataset approach
  - Safety limits (500KB, 1.25MB)
  - Custom GPT integration instructions
- **Path:** `docs/DATASET_MANIFEST_GUIDE.md`

### 3. **DATASET_DISCOVERY.md** 📊 HIGH PRIORITY
- **Purpose:** Available datasets, paths, and query patterns
- **Why:** Lists all datasets (ELI, SAOS) with exact blob paths and examples
- **Key info:**
  - ELI: 40K+ legislative acts
  - SAOS: 20K judgments
  - Prefix-based navigation
- **Status:** ✅ Updated to recommend query_dataset
- **Path:** `docs/DATASET_DISCOVERY.md`

### 4. **ELI_USAGE_GUIDE.md** 📚 HIGH PRIORITY
- **Purpose:** Complete ELI dataset usage guide
- **Why:** Shows recommended patterns for Polish legislation queries
- **Key info:**
  - query_dataset examples
  - Citation formats
  - Performance notes
- **Status:** ✅ Updated with query_dataset as default
- **Path:** `docs/ELI_USAGE_GUIDE.md`

## Supplementary Files (Nice to Have)

### 5. **QUERY_DATASET.md** (if exists)
- Detailed explanation of the unified query_dataset tool
- Parameter reference
- fetch_content usage

### 6. **IMPLEMENTATION_QUERY_DATASET.md**
- Technical implementation details
- Backward compatibility notes
- Migration path from eli_acts_query

### 7. **ELI_INTEGRATION_SUMMARY.md**
- ELI dataset overview
- Data sources and update frequency
- Field descriptions

## Files NOT Recommended for Knowledge Base

❌ **Internal/Development Files:**
- `*.py` scripts (server-side code)
- Test files (`test_*.py`)
- Local settings (`local.settings.json`)
- Build artifacts

❌ **Raw Data:**
- Actual JSONL indexes (too large)
- Page dumps (multi-MB files)

❌ **Legacy/Deprecated:**
- Old examples using `read_blob_file`
- Documents referencing only `eli_acts_query` without query_dataset

## Custom GPT Instructions Template

Add this to your Custom GPT system instructions:

```markdown
# OmniFlow Central - Legal Research Tools

You have access to Polish legal datasets via OmniFlow Central API.

## Available Datasets
1. **eli_acts** - 40,000+ Polish legislative acts (Sejm)
2. **saos_judgments** - 20,000 court judgments (Supreme Administrative Court)

## Primary Tool: query_dataset

**Always use query_dataset with fetch_content=true for best performance:**

```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "eli_acts",
    "q": "<search query>",
    "year": <year>,
    "limit": 10,
    "fetch_content": true
  }
}
```

### For Court Judgments:
```json
{
  "tool": "query_dataset",
  "params": {
    "dataset": "saos_judgments",
    "q": "<search query>",
    "court": "<court name>",
    "limit": 10,
    "fetch_content": true
  }
}
```

## Legacy Tools (avoid)
- `eli_acts_query` - deprecated, use query_dataset instead
- `read_blob_file` - doesn't exist, use read_blob via tools/call

## Safety Limits
- Single file reads: 500 KB cap
- Multiple files: 1.25 MB total cap
- Always set reasonable `limit` values (default 10, max 50)

## Citation Format
Always cite sources with:
- ELI identifier (e.g., DU/2025/1234)
- Display address (e.g., Dz.U. 2025 poz. 1234)
- Status (obowiązujący/uchylony)
- Official source URL when available
```

## Attachment Checklist

Before uploading to Custom GPT:

- [ ] openapi_tools_call.yaml
- [ ] DATASET_MANIFEST_GUIDE.md
- [ ] DATASET_DISCOVERY.md  
- [ ] ELI_USAGE_GUIDE.md
- [ ] (Optional) QUERY_DATASET.md
- [ ] (Optional) IMPLEMENTATION_QUERY_DATASET.md

## Update Policy

**When to refresh knowledge base:**
1. When new datasets are added (e.g., SAOS per-judgment structure)
2. When API endpoints change
3. When safety limits are modified
4. After manifest structure updates

**Current version:** 2026-01-07 (query_dataset unified approach)

## Quick Reference Card

| Task | Tool | Key Parameters |
|------|------|----------------|
| Search legislation | query_dataset | dataset=eli_acts, q, year, fetch_content=true |
| Search judgments | query_dataset | dataset=saos_judgments, q, court, fetch_content=true |
| Discover datasets | dataset_search | user_id=public, tags_any=[...] |
| List files | list_blobs | prefix=datasets/..., max_results |
| Read single file | read_blob | name=datasets/... |
| Read multiple files | read_many_blobs | files=[...], parse_json=true |

**Default user_id:** Use "public" for shared datasets, "default" for user-specific data.
