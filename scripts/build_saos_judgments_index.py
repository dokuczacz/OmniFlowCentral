#!/usr/bin/env python3
"""Build JSONL index from SAOS judgments pages in Azure cloud."""
import sys
import os
import json
import subprocess
import hashlib
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
    print("✓ Azure connection set")
except:
    print("⚠️ Failed to get Azure connection, using default config")

from OmniFlowCentral.shared.blob_ops import list_blobs, read_blob, upload_blob

USER_ID = 'default'
PAGES_PREFIX = 'datasets/saos/judgments/pages/'
INDEX_BLOB = 'datasets/saos/judgments/index/judgments_index.jsonl'
METADATA_BLOB = 'datasets/saos/judgments/metadata/index_build_summary.json'

def inspect_page_structure():
    """Inspect first page to understand structure."""
    print("\n📋 Inspecting page structure...")
    
    try:
        blob_result = read_blob(user_id=USER_ID, name=PAGES_PREFIX + 'page_00000.json')
        page_data = blob_result.get('data', {})
        
        print(f"   Top-level keys: {list(page_data.keys())}")
        print(f"   Items count: {len(page_data.get('items', []))}")
        
        if page_data.get('items'):
            first_item = page_data['items'][0]
            print(f"   Sample judgment keys ({len(first_item.keys())} total):")
            for i, key in enumerate(list(first_item.keys())[:20]):
                val = first_item[key]
                val_preview = str(val)[:50] if val else "None"
                print(f"     {key}: {val_preview}")
            
            return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def build_index():
    """Build JSONL index from all pages."""
    print("\n🔨 Building JSONL index...")
    
    # List all pages
    pages = list_blobs(user_id=USER_ID, prefix=PAGES_PREFIX, max_results=250)
    print(f"   Found {len(pages)} pages to process")
    
    if not pages:
        print("   ❌ No pages found!")
        return False
    
    # Collect all judgments
    all_judgments = []
    processed_pages = 0
    
    for i, page_blob in enumerate(sorted(pages, key=lambda x: x['name'])):
        page_name = page_blob['name']
        
        try:
            blob_result = read_blob(user_id=USER_ID, name=page_name)
            page_data = blob_result.get('data', {})
            items = page_data.get('items', [])
            
            # Extract key fields for index (minimal but searchable)
            for item in items:
                judgment_index = {
                    'id': item.get('id'),
                    'courtCases': item.get('courtCases', []),
                    'judgmentType': item.get('judgmentType'),
                    'judgmentDate': item.get('judgmentDate'),
                    'courtType': item.get('courtType'),
                    'division': item.get('division', {}).get('name') if item.get('division') else None,
                    'judges': [j.get('name') for j in item.get('judges', []) if j.get('name')],
                    'referencedRegulations': item.get('referencedRegulations', []),
                    'keywords': item.get('keywords', []),
                    'textContent': item.get('textContent', '')[:500] if item.get('textContent') else '',  # First 500 chars
                    'source_page': page_name
                }
                all_judgments.append(judgment_index)
            
            processed_pages += 1
            
            if (i + 1) % 50 == 0:
                print(f"   ... processed {i + 1}/{len(pages)} pages ({len(all_judgments)} judgments)")
        
        except Exception as e:
            print(f"   ⚠️ Error processing {page_name}: {e}")
            continue
    
    print(f"   ✓ Processed {processed_pages} pages, extracted {len(all_judgments)} judgments")
    
    # Build JSONL
    jsonl_lines = [json.dumps(j, ensure_ascii=False) for j in all_judgments]
    jsonl_content = '\n'.join(jsonl_lines)
    jsonl_bytes = jsonl_content.encode('utf-8')
    
    size_mb = len(jsonl_bytes) / 1024 / 1024
    print(f"   Index size: {size_mb:.1f} MB ({len(all_judgments)} items)")
    
    # Calculate hash
    sha256 = hashlib.sha256(jsonl_bytes).hexdigest()
    print(f"   SHA256: {sha256[:16]}...")
    
    # Upload index
    print(f"\n📤 Uploading index to Azure...")
    try:
        upload_blob(
            user_id=USER_ID,
            blob_name=INDEX_BLOB,
            data=jsonl_bytes,
            content_type='application/jsonl'
        )
        print(f"   ✓ Index uploaded: {INDEX_BLOB}")
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        return False
    
    # Create metadata summary
    metadata = {
        'build_date': datetime.utcnow().isoformat() + 'Z',
        'total_pages': processed_pages,
        'total_judgments': len(all_judgments),
        'index_size_bytes': len(jsonl_bytes),
        'index_size_mb': round(size_mb, 2),
        'sha256': sha256,
        'index_blob': INDEX_BLOB,
        'source_prefix': PAGES_PREFIX
    }
    
    try:
        upload_blob(
            user_id=USER_ID,
            blob_name=METADATA_BLOB,
            data=json.dumps(metadata, indent=2).encode('utf-8'),
            content_type='application/json'
        )
        print(f"   ✓ Metadata uploaded: {METADATA_BLOB}")
    except Exception as e:
        print(f"   ⚠️ Metadata upload failed: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ INDEX BUILD COMPLETE")
    print(f"   Pages: {processed_pages}")
    print(f"   Judgments: {len(all_judgments)}")
    print(f"   Index: {size_mb:.1f} MB")
    print(f"   Path: users/{USER_ID}/{INDEX_BLOB}")
    print(f"{'='*60}")
    
    return True

def main():
    print("SAOS Judgments Index Builder")
    print("=" * 60)
    
    # Step 1: Inspect structure
    if not inspect_page_structure():
        print("\n❌ Failed to inspect page structure")
        return 1
    
    # Step 2: Confirm build
    print("\n" + "=" * 60)
    user_input = input("Proceed with index build? [y/N]: ").strip().lower()
    
    if user_input != 'y':
        print("Cancelled.")
        return 0
    
    # Step 3: Build index
    if not build_index():
        print("\n❌ Index build failed")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
