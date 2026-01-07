#!/usr/bin/env python3
"""Build JSONL index from SAOS judgments pages in Azure blob storage."""
import sys
import os
import json
import hashlib
import subprocess
from datetime import datetime

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, repo_root)

# Set Azure connection before imports
try:
    result = subprocess.run(
        ['powershell', '-Command', 
         'az storage account show-connection-string --name agentresourcegroup89c2 --resource-group agentresourcegroup --output tsv'],
        capture_output=True, text=True, check=True, shell=True
    )
    os.environ['AZURE_STORAGE_CONNECTION_STRING'] = result.stdout.strip()
    print("✓ Azure connection configured")
except:
    print("⚠️ Using default connection (might be Azurite)")

from OmniFlowCentral.shared.blob_ops import list_blobs, read_blob, upload_blob

USER_ID = 'default'
PAGES_PREFIX = 'datasets/saos/judgments/pages/'
INDEX_NAME = 'datasets/saos/judgments/index/judgments_index.jsonl'
METADATA_NAME = 'datasets/saos/judgments/metadata/index_summary.json'

def build_index():
    """Build JSONL index from all judgment pages."""
    print(f"\n{'='*60}")
    print("SAOS Judgments Index Builder")
    print(f"{'='*60}\n")
    
    # List all pages
    print(f"📦 Listing judgment pages...")
    pages = list_blobs(user_id=USER_ID, prefix=PAGES_PREFIX, max_results=250)
    print(f"   Found {len(pages)} pages\n")
    
    if len(pages) == 0:
        print("❌ No pages found!")
        return 1
    
    # Confirm before proceeding
    print(f"⚠️  This will:")
    print(f"   - Read {len(pages)} pages from Azure")
    print(f"   - Extract ~{len(pages) * 100} judgment records")
    print(f"   - Build JSONL index (~300-400 MB)")
    print(f"   - Upload to: {INDEX_NAME}")
    print(f"\n   Estimated time: ~5-10 minutes")
    
    confirm = input(f"\n▶ Continue? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("❌ Cancelled by user")
        return 0
    
    print(f"\n🔨 Building index...\n")
    
    # Process pages
    all_items = []
    errors = []
    
    for i, page_meta in enumerate(pages, 1):
        page_name = page_meta['name']
        page_file = page_name.split('/')[-1]
        
        print(f"   [{i}/{len(pages)}] {page_file}...", end=' ', flush=True)
        
        try:
            # Read page (with user prefix)
            result = read_blob(name=f"users/{USER_ID}/{page_name}", user_id=USER_ID)
            
            # Extract data
            if isinstance(result, dict) and 'data' in result:
                page_data = result['data']
            else:
                page_data = result
            
            # Parse JSON if string
            if isinstance(page_data, str):
                page_data = json.loads(page_data)
            
            # Extract items from SAOS API response structure
            if isinstance(page_data, dict):
                items = page_data.get('items', [])
            elif isinstance(page_data, list):
                items = page_data
            else:
                print(f"⚠️ unexpected structure")
                errors.append(f"{page_file}: unexpected data type {type(page_data)}")
                continue
            
            all_items.extend(items)
            print(f"✓ {len(items)} items")
            
        except Exception as e:
            print(f"❌ {str(e)[:50]}")
            errors.append(f"{page_file}: {str(e)}")
    
    if len(all_items) == 0:
        print("\n❌ No items extracted!")
        return 1
    
    print(f"\n📊 Extracted {len(all_items)} total judgments")
    
    # Build JSONL
    print(f"\n📝 Writing JSONL index...")
    jsonl_lines = [json.dumps(item, ensure_ascii=False) for item in all_items]
    jsonl_content = '\n'.join(jsonl_lines)
    jsonl_bytes = jsonl_content.encode('utf-8')
    
    size_mb = len(jsonl_bytes) / 1024 / 1024
    print(f"   Size: {size_mb:.1f} MB")
    print(f"   Items: {len(all_items)}")
    
    # Calculate hash
    sha256 = hashlib.sha256(jsonl_bytes).hexdigest()
    print(f"   SHA256: {sha256[:16]}...")
    
    # Upload index
    print(f"\n📤 Uploading index to Azure...")
    upload_blob(
        name=INDEX_NAME,
        content=jsonl_bytes,
        user_id=USER_ID
    )
    print(f"   ✓ Uploaded to {INDEX_NAME}")
    
    # Create metadata summary
    metadata = {
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'total_items': len(all_items),
        'total_pages': len(pages),
        'index_size_bytes': len(jsonl_bytes),
        'index_size_mb': round(size_mb, 2),
        'sha256': sha256,
        'errors': errors if errors else None,
        'sample_judgment_id': all_items[0].get('id') if all_items else None
    }
    
    print(f"\n📋 Creating metadata summary...")
    upload_blob(
        name=METADATA_NAME,
        content=json.dumps(metadata, indent=2, ensure_ascii=False).encode('utf-8'),
        user_id=USER_ID
    )
    print(f"   ✓ Uploaded to {METADATA_NAME}")
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"✅ INDEX BUILD COMPLETE")
    print(f"{'='*60}")
    print(f"  Pages processed: {len(pages)}")
    print(f"  Items indexed: {len(all_items)}")
    print(f"  Index size: {size_mb:.1f} MB")
    print(f"  Index path: users/{USER_ID}/{INDEX_NAME}")
    print(f"  Errors: {len(errors)}")
    
    if errors:
        print(f"\n⚠️  Errors encountered:")
        for err in errors[:5]:
            print(f"   - {err}")
        if len(errors) > 5:
            print(f"   ... and {len(errors)-5} more")
    
    print(f"\n✓ Index ready for saos_judgments_query tool!")
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(build_index())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
