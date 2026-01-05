# ELI dataset handover

Overview:

- The Sejm ELI dataset (`inForce=1`) is now ingested under Azure blob `omniflowcentralcustomgpt` as:
  - `users/public/datasets/eli_acts/pages/*.json` — raw API responses (`offset,count,totalCount,items`).
  - `users/public/datasets/eli_acts/index/acts_inforce_1.jsonl` — consolidated JSONL index (1 ActInfo per line).
  - `users/public/datasets/eli_acts/runs/<timestamp>.json` — run metadata, checksum, query params.
- Scripts:
  - `scripts/eli_dump_to_blob.py` (streaming downloader + optional JSONL index + run metadata, can resume from offset).
  - `scripts/eli_index_export.py` (reads stored pages to produce a local `data/eli_acts_index.jsonl`).
  - `scripts/eli_index_to_md.py` (renders latest run + sample rows into `docs/eli_acts_export.md`).
  - Markdown samples reside in `docs/eli_acts_sample.md`, `docs/eli_act_details_one.md`, `docs/eli_acts_data_export.md`.

Current state:

- Latest recorded run ID: `20260104T012816Z` (118 pages, `last_offset=59000`, JSONL count=59000).
- Partial local dump available; you can continue with `python scripts/eli_dump_to_blob.py --offset 59000 --write-index-jsonl`.
- JSONL index is stored under the `index/` path (check `run_meta` for `items_jsonl.blob_name`).
- A sample `Act` detail (DU/2025/1900) already documented in `docs/eli_act_details_one.md`.
- `README.md` has instructions for running both `eli_dump_to_blob.py` and `eli_index_export.py`, plus pointers to summaries.

Next steps for incoming agent:

1. **Expose dataset through OmniFlowCentral tools**
   - Add a `eli_acts_query` tool: handle params (`q`, `year`, `publisher`, `status`, `limit`) and respond with matching `ActInfo` hits plus provenance (blob path, offset).
   - Register spec in `OmniFlowCentral/shared/tool_specs.py` so Custom GPT can discover it.
   - Keep authentication via function key (no OAuth needed for ELI).

2. **Use dataset search experience**
   - Optionally add an entry to the manifest (`upload_data_or_file`/`upsert_manifest_entry`) so `dataset_search` surfaces the ELI dataset (category `dataset`, tag `eli`).
   - Or extend `dataset_search` handling: when category/tag targets `eli_acts`, read `index/acts_inforce_1.jsonl` and filter (`title` contains `q`; optional filters on `publisher`, `year`, `status`).

3. **Connect GPT → OmniFlowCentral → dataset**
   - Custom GPT should first call `/api/tools/call` with `tool=dataset_search` to discover the dataset entry.
   - Then call `tool=eli_acts_query` (or the dataset-specific tool added above) to fetch hits; respond with the top results (max ~10) from the JSONL index.
   - Include metadata (ELI, title, status, dates, `displayAddress`) in the response to make it easy to cite sources.
   - Optionally add a follow-up tool (`eli_act_details`) that hits `GET /eli/acts/{publisher}/{year}/{position}` for richer metadata.

Implementation notes:

- The JSONL index contains sanitized `ActInfo` records from `/acts/search`; if you need `Act` details, call the detail endpoint on demand.
- Index updates should keep `runs/*.json` consistent (update `checksum.pages_fetched` and `items_jsonl` fields).
- Use the existing `AzureConfig` + blob ops helpers to read/write blobs.

Suggested commands:

```powershell
python scripts/eli_dump_to_blob.py --offset 59000 --max-pages 20 --write-index-jsonl
python scripts/eli_index_export.py --output data/eli_acts_index.jsonl
python scripts/eli_index_to_md.py
```

Once these steps run, the Markdown summary (`docs/eli_acts_export.md`) will capture the latest metadata for review.
