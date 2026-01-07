#!/usr/bin/env python3
"""Verify SAOS judgments import to Azure cloud."""
import sys
import os
import subprocess

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, repo_root)

# Set Azure connection string from az CLI before imports
try:
    result = subprocess.run(
        ['powershell', '-Command', 
         'az storage account show-connection-string --name agentresourcegroup89c2 --resource-group agentresourcegroup --output tsv'],
        capture_output=True, text=True, check=True, shell=True
    )
    os.environ['AZURE_STORAGE_CONNECTION_STRING'] = result.stdout.strip()
except:
    pass  # Will use default config

from OmniFlowCentral.shared.blob_ops import list_blobs
from OmniFlowCentral.shared.config import AzureConfig

def main():
    conn_str = AzureConfig.CONNECTION_STRING
    
    # Check connection
    if "127.0.0.1" in conn_str or "10000" in conn_str:
        print("⚠️ Using Azurite (local)")
    else:
        print("✓ Using Azure cloud")
    
    print(f"  Connection: {conn_str[:60]}...\n")
    
    # Check pages
    pages = list_blobs(user_id='default', prefix='datasets/saos/judgments/pages/', max_results=250)
    print(f"📦 SAOS Judgments Pages: {len(pages)}")
    
    if pages:
        recent = sorted(pages, key=lambda x: x.get("last_modified", ""), reverse=True)[:3]
        print(f"   Most recent:")
        for b in recent:
            name = b['name'].split('/')[-1]
            size_mb = b.get('size', 0) / 1024 / 1024
            print(f"   - {name} ({size_mb:.1f} MB)")
    
    # Check index
    index_blobs = list_blobs(user_id='default', prefix='datasets/saos/judgments/index/', max_results=10)
    print(f"\n📑 SAOS Judgments Index: {len(index_blobs)}")
    
    if index_blobs:
        for idx in index_blobs:
            name = idx['name'].split('/')[-1]
            size_mb = idx.get('size', 0) / 1024 / 1024
            print(f"   - {name} ({size_mb:.1f} MB)")
    else:
        print("   ⚠️ No index files found - need to build index!")
    
    # Check metadata
    meta_blobs = list_blobs(user_id='default', prefix='datasets/saos/judgments/metadata/', max_results=10)
    print(f"\n📋 SAOS Judgments Metadata: {len(meta_blobs)}")
    
    if meta_blobs:
        for m in meta_blobs:
            name = m['name'].split('/')[-1]
            size_kb = m.get('size', 0) / 1024
            print(f"   - {name} ({size_kb:.1f} KB)")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Pages: {len(pages)} (should be 200)")
    print(f"  Index: {len(index_blobs)} (should be 1-2)")
    print(f"  Metadata: {len(meta_blobs)} (should be 1+)")
    
    if len(pages) >= 200 and len(index_blobs) >= 1:
        print(f"\n✅ Import looks GOOD - data ready for CustomGPT!")
    elif len(pages) >= 200:
        print(f"\n⚠️ Pages OK but INDEX MISSING - run index builder")
    else:
        print(f"\n❌ Import INCOMPLETE - expected 200 pages")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
