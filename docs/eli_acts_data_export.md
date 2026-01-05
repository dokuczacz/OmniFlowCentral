# ELI acts export (inForce=1)

This document summarizes what was extracted so far from the Sejm ELI API and stored in Azurite under `users/public/datasets/eli_acts/`.

## Blobs created

- `pages/acts_offset_<offset>.json`: raw API responses (500 records per file) with `offset`, `count`, `totalCount` and the `items` array.
- `index/acts_inforce_1.jsonl`: consolidated JSONL index (1 act per line) built either by `eli_dump_to_blob.py --write-index-jsonl` or `scripts/eli_index_export.py`.
- `runs/<timestamp>.json`: run metadata + checksum (pages fetched, last offset, index SHA-256, query params).

The latest recorded run metadata is:

```json
{
  "run_id": "20260104T012816Z",
  "source": {
    "base_url": "https://api.sejm.gov.pl/eli",
    "endpoint": "/acts/search"
  },
  "query": {
    "inForce": "1",
    "limit": 500,
    "offset": 0
  },
  "checksum": {
    "pages_fetched": 118,
    "last_offset": 59000,
    "items_jsonl": {
      "enabled": true,
      "blob_name": "datasets/eli_acts/index/acts_inforce_1.jsonl",
      "count": 59000,
      "size_bytes": 72367441,
      "sha256": "3764f7c2819db49ac0969d3008e028b8761b7a1a7e80e00a117cb5c45deb2948"
    }
  }
}
```

## Sample records (JSONL)

The first few lines of `index/acts_inforce_1.jsonl` contain the detailed `ActInfo` payloads. Here are the first three entries:

| ELI | Title | Year | Status | Promulgation |
| --- | ----- | ---- | ------ | ------------ |
| DU/2025/1900 | Obwieszczenie Marszałka Sejmu ... o finansowaniu społecznościowym dla przedsięwzięć gospodarczych i pomocy kredytobiorcom | 2025 | obowiązujący | 2025-12-31 |
| DU/2025/1899 | Obwieszczenie Marszałka Sejmu ... w sprawie ogłoszenia jednolitego tekstu ustawy o finansowaniu zrównoważonym | 2025 | obowiązujący | 2025-12-29 |
| DU/2025/1898 | Obwieszczenie ... w sprawie ogłoszenia jednolitego tekstu ustawy o przeciwdziałaniu praniu pieniędzy | 2025 | obowiązujący | 2025-12-28 |

(*titles truncated for readability—refer to the JSONL file for full text.*)

## Single-act detail example

The API detail endpoint `GET /acts/{publisher}/{year}/{position}` returns richer metadata for each act. For example, `DU/2025/1900` contains:

```json
{
  "ELI": "DU/2025/1900",
  "address": "WDU20250001900",
  "title": "Obwieszczenie Marszałka Sejmu ... pomoc kredytobiorcom",
  "status": "obowiązujący",
  "inForce": "IN_FORCE",
  "promulgation": "2025-12-31",
  "announcementDate": "2025-12-19",
  "changeDate": "2026-01-02T11:20:03",
  "texts": [
    {"fileName": "D20251900.pdf", "type": "O"},
    {"fileName": "D20251900.pdf", "type": "I"},
    {"fileName": "D20251900L.pdf", "type": "T"}
  ]
}
```

## Next steps

1. Use `python scripts/eli_dump_to_blob.py --offset <next> --write-index-jsonl` to append new pages and keep the JSONL index/current run metadata up to date.
2. Run `python scripts/eli_index_export.py --output data/eli_acts_index.jsonl` to reproduce the flat index locally (the script reads all stored pages).
3. If you need a Markdown digest for sharing, run `python scripts/eli_index_to_md.py` to re-create `docs/eli_acts_export.md` with live metadata and sample rows.

The conversion is deterministic: every page is stored under `users/{user_id}/datasets/eli_acts/pages/`, the index lives under `index/`, and metadata under `runs/`. You can continue the export from `last_offset` as needed.
