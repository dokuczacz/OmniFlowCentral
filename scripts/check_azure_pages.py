#!/usr/bin/env python3
"""Quick check of how many pages are in Azure cloud."""
import sys
import os

# Add repo root to path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, repo_root)

# Try to get Azure connection string from environment (set by PowerShell)
azure_conn = os.environ.get('AZURE_STORAGE_CONNECTION_STRING', '')
if not azure_conn or 'devstoreaccount1' in azure_conn.lower():
    print("⚠️ WARNING: AZURE_STORAGE_CONNECTION_STRING not set or points to Azurite")
    print("   Run this in PowerShell first:")
    print("   $env:AZURE_STORAGE_CONNECTION_STRING = (az storage account show-connection-string --name agentresourcegroup89c2 --resource-group agentresourcegroup --output tsv)")
    sys.exit(1)

from OmniFlowCentral.shared.blob_ops import list_blobs
from OmniFlowCentral.shared.config import AzureConfig

def main():
    # Ensure we're using Azure cloud connection
    conn_str = AzureConfig.CONNECTION_STRING
    if "127.0.0.1" in conn_str or "10000" in conn_str:
        print("⚠️ WARNING: Still using Azurite connection!")
        print(f"Connection: {conn_str[:50]}...")
        return 1
    
    print(f"✓ Using Azure cloud connection")
    print(f"  {conn_str[:50]}...")
    
    # List pages
    blobs = list_blobs(user_id='default', prefix='datasets/saos/judgments/pages/', max_results=250)
    print(f"\n📦 Total pages in Azure cloud: {len(blobs)}")
    
    # Show most recent
    recent = sorted(blobs, key=lambda x: x.get("last_modified", ""), reverse=True)[:5]
    print(f"\n🕒 Most recent 5 pages:")
    for b in recent:
        print(f"  - {b['name']}")
        print(f"    Modified: {b.get('last_modified', '?')}")
        print(f"    Size: {b.get('size', 0)/1024:.1f} KB")
    
    # Check index
    index_blobs = list_blobs(user_id='default', prefix='datasets/saos/judgments/index/', max_results=10)
    print(f"\n📑 Index files: {len(index_blobs)}")
    for idx in index_blobs:
        print(f"  - {idx['name']}")
        print(f"    Size: {idx.get('size', 0)/1024/1024:.1f} MB")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
