#!/usr/bin/env python3
"""
SAOS Index Builder
==================
Reads page_*.json files from datasets/saos/judgments/pages/ and builds a consolidated
NDJSON index at datasets/saos/judgments/index/judgments_index.jsonl.

Each line in the index is a single judgment record with fields:
- caseNumber
- court
- courtType
- judgmentDate
- summary
- keywords
- judges
- pageId (source page file)
- recordIndex (position in original page array)

Usage:
    python scripts/saos_build_index.py [--max-pages N] [--write-index]
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from azure.core.exceptions import ResourceNotFoundError
from OmniFlowCentral.shared.blob_ops import ToolError
from OmniFlowCentral.shared.config import AzureConfig
from OmniFlowCentral.shared.data_ops import _connect_container

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)


def extract_judgment_record(judgment: dict, page_id: str, record_index: int) -> dict:
    """Extract key fields from a SAOS judgment object."""
    return {
        "caseNumber": judgment.get("caseNumber", ""),
        "court": judgment.get("court", {}).get("name", ""),
        "courtType": judgment.get("court", {}).get("type", ""),
        "judgmentDate": judgment.get("judgmentDate", ""),
        "summary": judgment.get("summary", ""),
        "keywords": judgment.get("keywords", []),
        "judges": [j.get("name", "") for j in judgment.get("judges", [])],
        "pageId": page_id,
        "recordIndex": record_index,
    }


def build_index_from_blob(container_client, max_pages: int = None):
    """
    Read page_*.json blobs and yield individual judgment records.
    
    Args:
        container_client: Azure container client
        max_pages: Optional limit on number of pages to process
        
    Yields:
        dict: Individual judgment records
    """
    prefix = "datasets/saos/judgments/pages/"
    log.info(f"Listing blobs with prefix: {prefix}")
    
    blobs = container_client.list_blobs(name_starts_with=prefix)
    blob_names = sorted([b.name for b in blobs if b.name.endswith(".json")])
    
    if max_pages:
        blob_names = blob_names[:max_pages]
    
    log.info(f"Found {len(blob_names)} page files to process")
    
    total_judgments = 0
    
    for blob_name in blob_names:
        page_id = Path(blob_name).stem  # e.g., "page_00000"
        log.info(f"Processing {blob_name}...")
        
        try:
            blob_client = container_client.get_blob_client(blob_name)
            raw_data = blob_client.download_blob().readall()
            judgments = json.loads(raw_data.decode("utf-8"))
            
            if not isinstance(judgments, list):
                log.warning(f"Skipping {blob_name}: not a JSON array")
                continue
            
            for idx, judgment in enumerate(judgments):
                if not isinstance(judgment, dict):
                    continue
                record = extract_judgment_record(judgment, page_id, idx)
                yield record
                total_judgments += 1
            
            log.info(f"  → Extracted {len(judgments)} judgments from {page_id}")
        
        except ResourceNotFoundFound:
            log.warning(f"Blob not found: {blob_name}")
            continue
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error in {blob_name}: {e}")
            continue
        except Exception as e:
            log.error(f"Error processing {blob_name}: {e}")
            continue
    
    log.info(f"Total judgments extracted: {total_judgments}")


def write_index_to_blob(container_client, records_generator, output_blob_name: str):
    """
    Write NDJSON index to blob storage.
    
    Args:
        container_client: Azure container client
        records_generator: Generator yielding judgment records
        output_blob_name: Target blob path for the index
    """
    log.info(f"Writing index to {output_blob_name}...")
    
    lines = []
    count = 0
    
    for record in records_generator:
        line = json.dumps(record, ensure_ascii=False, separators=(',', ':'))
        lines.append(line)
        count += 1
        
        if count % 1000 == 0:
            log.info(f"  → {count} records processed...")
    
    ndjson_content = "\n".join(lines)
    blob_client = container_client.get_blob_client(output_blob_name)
    blob_client.upload_blob(
        ndjson_content.encode("utf-8"),
        overwrite=True,
        content_settings={'content_type': 'application/x-ndjson'}
    )
    
    log.info(f"✅ Index written successfully: {count} records, {len(ndjson_content)} bytes")
    return count


def main():
    parser = argparse.ArgumentParser(description="Build SAOS judgments NDJSON index from page files")
    parser.add_argument("--max-pages", type=int, help="Limit number of pages to process")
    parser.add_argument("--write-index", action="store_true", help="Write index to blob storage")
    parser.add_argument(
        "--output",
        default="datasets/saos/judgments/index/judgments_index.jsonl",
        help="Output blob path for index (default: datasets/saos/judgments/index/judgments_index.jsonl)"
    )
    args = parser.parse_args()
    
    if not AzureConfig.CONNECTION_STRING:
        log.error("Missing AZURE_STORAGE_CONNECTION_STRING or AzureWebJobsStorage env var")
        sys.exit(1)
    
    try:
        container_client = _connect_container()
    except ToolError as e:
        log.error(f"Failed to connect to storage: {e.message}")
        sys.exit(1)
    
    records_gen = build_index_from_blob(container_client, max_pages=args.max_pages)
    
    if args.write_index:
        count = write_index_to_blob(container_client, records_gen, args.output)
        log.info(f"Index build complete: {count} judgments indexed")
    else:
        # Dry run: just count
        count = sum(1 for _ in records_gen)
        log.info(f"Dry run complete: {count} judgments would be indexed")
        log.info("Run with --write-index to upload to blob storage")


if __name__ == "__main__":
    main()
