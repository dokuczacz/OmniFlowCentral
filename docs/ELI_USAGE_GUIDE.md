# Using ELI Acts Dataset in Custom GPT

This guide shows how to query the Polish legislative acts dataset from a Custom GPT.

## Quick Start

### 1. Discover Available Datasets

**Request:**
```http
POST /api/tools/call
Content-Type: application/json
x-functions-key: YOUR_FUNCTION_KEY

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

**Response:**
```json
{
  "status": "success",
  "tool": "dataset_search",
  "user_id": "public",
  "result": {
    "status": "success",
    "user_id": "public",
    "total": 1,
    "hits": [
      {
        "blob_name": "datasets/eli_acts/index/acts_inforce_1.jsonl",
        "display_name": "ELI Legislative Acts (Sejm)",
        "summary": "Polish legislative acts dataset from Sejm ELI API - acts with inForce=1 status",
        "tags": ["eli", "legislation", "sejm", "poland"],
        "category": "dataset",
        "metadata": {
          "tool": "eli_acts_query",
          "record_count": 59000
        }
      }
    ]
  }
}
```

### 2. Query the ELI Dataset

**Request:**
```http
POST /api/tools/call
Content-Type: application/json
x-functions-key: YOUR_FUNCTION_KEY

{
  "tool": "eli_acts_query",
  "payload": {
    "params": {
      "q": "podatek",
      "year": 2025,
      "limit": 5
    }
  }
}
```

**Response:**
```json
{
  "status": "success",
  "tool": "eli_acts_query",
  "user_id": "default",
  "result": {
    "status": "success",
    "dataset": "eli_acts",
    "total_scanned": 59000,
    "total_returned": 5,
    "limit": 5,
    "hits": [
      {
        "ELI": "DU/2025/1234",
        "title": "Ustawa o podatku dochodowym...",
        "publisher": "DU",
        "year": 2025,
        "pos": 1234,
        "status": "obowiązujący",
        "displayAddress": "Dz.U. 2025 poz. 1234",
        "promulgation": "2025-06-15",
        "announcementDate": "2025-06-01",
        "changeDate": "2025-12-20T10:15:30",
        "type": "Ustawa"
      }
    ],
    "provenance": {
      "blob_path": "users/public/datasets/eli_acts/index/acts_inforce_1.jsonl",
      "source": "https://api.sejm.gov.pl/eli/acts/search"
    }
  }
}
```

## Query Parameters

| Parameter   | Type   | Description                          | Example           |
|-------------|--------|--------------------------------------|-------------------|
| `q`         | string | Search term in title (case-insensitive) | "ustaw"          |
| `year`      | int    | Filter by year                       | 2025              |
| `publisher` | string | Filter by publisher (uppercase)      | "DU"              |
| `status`    | string | Filter by status (lowercase)         | "obowiązujący"    |
| `limit`     | int    | Max results (default 10, max 50)     | 20                |

## Common Use Cases

### Search by Keyword
```json
{
  "tool": "eli_acts_query",
  "payload": {
    "params": {
      "q": "energia",
      "limit": 10
    }
  }
}
```

### Filter by Year
```json
{
  "tool": "eli_acts_query",
  "payload": {
    "params": {
      "year": 2024,
      "limit": 20
    }
  }
}
```

### Find Recent Acts
```json
{
  "tool": "eli_acts_query",
  "payload": {
    "params": {
      "year": 2026,
      "status": "obowiązujący",
      "limit": 10
    }
  }
}
```

### Search in Specific Publisher
```json
{
  "tool": "eli_acts_query",
  "payload": {
    "params": {
      "publisher": "DU",
      "q": "rozporządzenie",
      "limit": 15
    }
  }
}
```

## Response Fields

Each hit in the results contains:

- **ELI**: European Legislation Identifier (e.g., "DU/2025/1234")
- **title**: Full title of the act (Polish)
- **publisher**: Publisher code (e.g., "DU" = Dziennik Ustaw)
- **year**: Year of publication
- **pos**: Position number
- **status**: Current status (e.g., "obowiązujący" = in force)
- **displayAddress**: Human-readable citation (e.g., "Dz.U. 2025 poz. 1234")
- **promulgation**: Promulgation date (ISO 8601)
- **announcementDate**: Announcement date (ISO 8601)
- **changeDate**: Last change date (ISO 8601)
- **type**: Type of act (e.g., "Ustawa", "Rozporządzenie", "Obwieszczenie")

## Error Handling

### Dataset Not Found
If the index hasn't been created yet:
```json
{
  "status": "error",
  "code": "NOT_FOUND",
  "message": "ELI acts index not found at users/public/datasets/eli_acts/index/acts_inforce_1.jsonl. Please run eli_dump_to_blob.py first."
}
```

**Solution:** Run the data import script:
```bash
python scripts/eli_dump_to_blob.py --write-index-jsonl
```

### Invalid Parameters
```json
{
  "status": "error",
  "code": "VALIDATION_FAILED",
  "message": "Invalid parameter value"
}
```

## Dataset Information

- **Source:** Sejm ELI API (https://api.sejm.gov.pl/eli/acts/search)
- **Query:** `inForce=1` (only acts currently in force)
- **Format:** JSONL (JSON Lines)
- **Size:** ~59,000 records (~70 MB)
- **Update Frequency:** Manual (run import script to refresh)
- **Language:** Polish

## Integration with Custom GPT

In your Custom GPT instructions:

```
When asked about Polish legislation, use these tools:

1. First, discover datasets:
   - Tool: dataset_search
   - Params: {"user_id": "public", "tags_any": ["eli"]}

2. Then query the ELI dataset:
   - Tool: eli_acts_query
   - Params: {"q": "<search_term>", "year": <year>, "limit": 10}

Always cite the source using the ELI identifier and displayAddress.
```

## Citing Results

When presenting results to users, include:

```
Found in: Dz.U. 2025 poz. 1234
ELI: DU/2025/1234
Status: Obowiązujący (in force)
Promulgated: 2025-06-15
```

## Performance Notes

- First query may take 1-2 seconds to load the index
- Subsequent queries are fast (<100ms)
- The entire dataset is scanned linearly
- For better performance with large result sets, use smaller `limit` values
- Title search is case-insensitive substring match

## Next Steps

For more details:
- Implementation: [`docs/ELI_INTEGRATION_SUMMARY.md`](ELI_INTEGRATION_SUMMARY.md)
- Data samples: [`docs/eli_acts_sample.md`](eli_acts_sample.md)
- Handover notes: [`docs/HANDOVER_ELI.md`](HANDOVER_ELI.md)
