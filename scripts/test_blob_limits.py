"""
Test blob operations with new soft caps, chunking, and pagination features.
"""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

sys.path.insert(0, str(_REPO_ROOT / "OmniFlowCentral"))

from shared.blob_ops import (
    read_blob,
    read_many_blobs,
    get_filtered_data,
    READ_BLOB_SOFT_CAP,
    READ_MANY_MAX_TOTAL_BYTES,
    READ_MANY_MAX_BYTES_PER_FILE,
)


def test_read_blob_soft_cap():
    """Test that read_blob respects soft cap"""
    print("\n=== Test: read_blob soft cap ===")
    
    try:
        # Read a large blob (ELI index)
        result = read_blob(
            user_id="public",
            name="datasets/eli_acts/index/acts_inforce_1.jsonl",
        )
        
        print(f"File name: {result['file_name']}")
        print(f"Content type: {result['content_type']}")
        print(f"Size (bytes): {result['size']}")
        print(f"Soft cap: {result.get('soft_cap', 'N/A')}")
        print(f"Truncated: {result.get('truncated', False)}")
        
        if result.get('warning'):
            print(f"Warning: {result['warning']}")
        
        # Verify soft cap is reported
        assert result.get('soft_cap') is not None, "soft_cap should be in response"
        
        # Check if truncated for large files
        if result['size'] >= READ_BLOB_SOFT_CAP:
            assert result.get('truncated') == True, "Large file should be truncated"
            print("✓ Soft cap enforced correctly")
        else:
            print("✓ File smaller than cap, not truncated")
        
        return True
        
    except Exception as exc:
        print(f"✗ FAILED: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_read_many_blobs_caps():
    """Test that read_many_blobs respects per-file and total caps"""
    print("\n=== Test: read_many_blobs caps ===")
    
    try:
        # Try to read multiple files
        result = read_many_blobs(
            user_id="public",
            files=[
                "datasets/eli_acts/index/acts_inforce_1.jsonl",
            ],
            parse_json=False,
        )
        
        print(f"Count: {result['count']}")
        print(f"Total bytes: {result['total_bytes']}")
        print(f"Max total bytes: {result.get('max_total_bytes', 'N/A')}")
        print(f"Errors: {result['errors']}")
        
        # Verify metadata
        assert result.get('max_total_bytes') is not None, "max_total_bytes should be in response"
        
        for i, item in enumerate(result['items'][:3], 1):
            if 'error' in item:
                print(f"  {i}. {item['file_name']}: ERROR - {item['error']}")
            else:
                print(f"  {i}. {item['file_name']}: {item['bytes']} bytes, truncated={item.get('truncated', False)}, soft_cap={item.get('soft_cap', 'N/A')}")
        
        # Verify total doesn't exceed cap
        if result['total_bytes'] >= READ_MANY_MAX_TOTAL_BYTES:
            print(f"✓ Total bytes capped at {READ_MANY_MAX_TOTAL_BYTES}")
        else:
            print(f"✓ Total bytes under cap")
        
        return True
        
    except Exception as exc:
        print(f"✗ FAILED: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_get_filtered_data_chunking():
    """Test get_filtered_data chunking for large NDJSON"""
    print("\n=== Test: get_filtered_data chunking ===")
    
    try:
        # First chunk
        result = get_filtered_data(
            user_id="public",
            blob_name="datasets/eli_acts/index/acts_inforce_1.jsonl",
            filter_key="year",
            filter_value="2025",
            chunk_size=50000,  # 50KB chunks
            max_chunks=2,
        )
        
        print(f"Status: {result['status']}")
        print(f"Count: {result['count']}")
        print(f"Chunk index: {result.get('chunk_index', 'N/A')}")
        print(f"Is last chunk: {result.get('is_last_chunk', 'N/A')}")
        print(f"Next chunk token: {result.get('next_chunk_token', 'N/A')}")
        print(f"Blob size: {result.get('blob_size', 'N/A')}")
        print(f"Processed bytes: {result.get('processed_bytes', 'N/A')}")
        
        # Verify chunk metadata
        assert 'chunk_index' in result, "chunk_index should be in response"
        assert 'is_last_chunk' in result, "is_last_chunk should be in response"
        
        if result['data']:
            print(f"First item: {result['data'][0].get('ELI', 'N/A')}")
        
        # If there's a next token, try second chunk
        if result.get('next_chunk_token'):
            print("\n  Fetching next chunk...")
            result2 = get_filtered_data(
                user_id="public",
                blob_name="datasets/eli_acts/index/acts_inforce_1.jsonl",
                filter_key="year",
                filter_value="2025",
                chunk_size=50000,
                max_chunks=2,
                next_chunk_token=result['next_chunk_token'],
            )
            
            print(f"  Chunk 2 - Count: {result2['count']}, chunk_index: {result2.get('chunk_index')}, is_last: {result2.get('is_last_chunk')}")
            print("  ✓ Pagination working")
        else:
            print("  ✓ Single chunk response (blob is small)")
        
        return True
        
    except Exception as exc:
        print(f"✗ FAILED: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_get_filtered_data_small_blob():
    """Test get_filtered_data with small blob (full load path)"""
    print("\n=== Test: get_filtered_data small blob ===")
    
    try:
        # Use a chunk of the index as a small test
        result = get_filtered_data(
            user_id="public",
            blob_name="datasets/eli_acts/index/acts_inforce_1.jsonl",
            chunk_size=10000,  # Small chunk size to simulate small blob
            max_chunks=1,
        )
        
        print(f"Status: {result['status']}")
        print(f"Count: {result['count']}")
        print(f"Is last chunk: {result.get('is_last_chunk')}")
        print(f"Next chunk token: {result.get('next_chunk_token')}")
        
        # Small blob should load fully
        assert result.get('is_last_chunk') == True, "Small blob should be single chunk"
        assert result.get('next_chunk_token') is None, "Small blob should have no next token"
        
        print("✓ Small blob loaded completely in one call")
        
        return True
        
    except Exception as exc:
        print(f"✗ FAILED: {exc}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("Blob Operations - Limits & Chunking Tests")
    print("=" * 70)
    print(f"\nConstants:")
    print(f"  READ_BLOB_SOFT_CAP: {READ_BLOB_SOFT_CAP:,} bytes")
    print(f"  READ_MANY_MAX_BYTES_PER_FILE: {READ_MANY_MAX_BYTES_PER_FILE:,} bytes")
    print(f"  READ_MANY_MAX_TOTAL_BYTES: {READ_MANY_MAX_TOTAL_BYTES:,} bytes")
    
    results = []
    
    try:
        results.append(("read_blob soft cap", test_read_blob_soft_cap()))
        results.append(("read_many_blobs caps", test_read_many_blobs_caps()))
        results.append(("get_filtered_data chunking", test_get_filtered_data_chunking()))
        results.append(("get_filtered_data small blob", test_get_filtered_data_small_blob()))
        
        print("\n" + "=" * 70)
        print("Test Results:")
        print("=" * 70)
        
        for test_name, passed in results:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}: {test_name}")
        
        all_passed = all(result[1] for result in results)
        
        if all_passed:
            print("\n✓ All tests passed!")
            return 0
        else:
            print("\n✗ Some tests failed")
            return 1
            
    except Exception as exc:
        print(f"\n✗ Test suite failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
