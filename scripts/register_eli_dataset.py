"""
Register the ELI acts dataset in the public user manifest.

This allows dataset_search to discover the ELI dataset with category='dataset' and tags=['eli', 'legislation'].
"""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from OmniFlowCentral.shared.data_ops import _connect_container
from OmniFlowCentral.shared.manifest_helper import (
    load_manifest,
    write_manifest,
    upsert_manifest_entry,
    _current_iso_timestamp,
)


def main():
    container_client = _connect_container()
    user_id = "public"
    
    # Load existing manifest
    manifest = load_manifest(container_client, user_id)
    
    # Check if ELI dataset already registered
    existing = None
    for entry in manifest.get("entries", []):
        if entry.get("blob_name") == "datasets/eli_acts/index/acts_inforce_1.jsonl":
            existing = entry
            break
    
    # Create or update entry
    now = _current_iso_timestamp()
    entry = {
        "blob_name": "datasets/eli_acts/index/acts_inforce_1.jsonl",
        "display_name": "ELI Legislative Acts (Sejm)",
        "summary": "Polish legislative acts dataset from Sejm ELI API - acts with inForce=1 status",
        "tags": ["eli", "legislation", "sejm", "poland"],
        "category": "dataset",
        "source": "https://api.sejm.gov.pl/eli/acts/search",
        "size": 0,  # Will be updated when JSONL is read
        "content_type": "application/x-ndjson",
        "updated_at": now,
        "created_at": existing.get("created_at") if existing else now,
        "manifest_tags": ["public", "legal"],
        "metadata": {
            "format": "jsonl",
            "record_count": 59000,
            "api_endpoint": "/eli/acts/search",
            "query_params": {"inForce": "1"},
            "tool": "eli_acts_query",
        },
    }
    
    # Update manifest
    upsert_manifest_entry(container_client, user_id, entry)
    
    print(f"✓ Registered ELI dataset in {user_id} manifest")
    print(f"  Display name: {entry['display_name']}")
    print(f"  Tags: {entry['tags']}")
    print(f"  Category: {entry['category']}")
    print(f"  Tool: {entry['metadata']['tool']}")


if __name__ == "__main__":
    main()
