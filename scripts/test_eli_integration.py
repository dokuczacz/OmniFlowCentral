"""
Test the ELI acts query integration.

Tests:
1. Query ELI dataset directly via eli_acts_query
2. Discover ELI dataset via dataset_search
3. Filter by year, publisher, status
4. Search by title keyword
"""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from OmniFlowCentral.shared.data_ops import dataset_search, eli_acts_query


def test_eli_acts_query_basic():
    """Test basic query without filters"""
    print("\n=== Test 1: Basic eli_acts_query (limit 3) ===")
    result = eli_acts_query({"limit": 3})
    print(f"Status: {result.get('status')}")
    print(f"Dataset: {result.get('dataset')}")
    print(f"Total scanned: {result.get('total_scanned')}")
    print(f"Total returned: {result.get('total_returned')}")
    print(f"\nFirst result:")
    if result.get('hits'):
        hit = result['hits'][0]
        print(f"  ELI: {hit.get('ELI')}")
        print(f"  Title: {hit.get('title')[:80]}...")
        print(f"  Status: {hit.get('status')}")
        print(f"  Year: {hit.get('year')}")
    print(f"\nProvenance: {result.get('provenance')}")
    return result


def test_eli_acts_query_year_filter():
    """Test filtering by year"""
    print("\n=== Test 2: Filter by year=2025 (limit 3) ===")
    result = eli_acts_query({"year": 2025, "limit": 3})
    print(f"Total returned: {result.get('total_returned')}")
    for i, hit in enumerate(result.get('hits', []), 1):
        print(f"  {i}. {hit.get('ELI')} - year={hit.get('year')}")
    return result


def test_eli_acts_query_publisher_filter():
    """Test filtering by publisher"""
    print("\n=== Test 3: Filter by publisher=DU (limit 3) ===")
    result = eli_acts_query({"publisher": "DU", "limit": 3})
    print(f"Total returned: {result.get('total_returned')}")
    for i, hit in enumerate(result.get('hits', []), 1):
        print(f"  {i}. {hit.get('ELI')} - publisher={hit.get('publisher')}")
    return result


def test_eli_acts_query_keyword():
    """Test keyword search in title"""
    print("\n=== Test 4: Search title for 'ustaw' (limit 3) ===")
    result = eli_acts_query({"q": "ustaw", "limit": 3})
    print(f"Total returned: {result.get('total_returned')}")
    for i, hit in enumerate(result.get('hits', []), 1):
        title = hit.get('title', '')[:70]
        print(f"  {i}. {hit.get('ELI')}")
        print(f"     {title}...")
    return result


def test_dataset_search_discovery():
    """Test discovering ELI dataset via dataset_search"""
    print("\n=== Test 5: Discover ELI dataset via dataset_search ===")
    result = dataset_search(user_id="public", params={"tags_any": ["eli"], "limit": 5})
    print(f"Status: {result.get('status')}")
    print(f"Total hits: {result.get('total')}")
    
    for hit in result.get('hits', []):
        if 'eli' in hit.get('tags', []):
            print(f"\nFound ELI dataset:")
            print(f"  Display name: {hit.get('display_name')}")
            print(f"  Summary: {hit.get('summary')}")
            print(f"  Tags: {hit.get('tags')}")
            print(f"  Category: {hit.get('category')}")
            print(f"  Blob: {hit.get('blob_name')}")
            metadata = hit.get('metadata', {})
            print(f"  Tool: {metadata.get('tool')}")
            print(f"  Record count: {metadata.get('record_count')}")
    return result


def test_combined_filters():
    """Test combining multiple filters"""
    print("\n=== Test 6: Combined filters (year=2024, status=obowiązujący, limit=2) ===")
    result = eli_acts_query({
        "year": 2024,
        "status": "obowiązujący",
        "limit": 2
    })
    print(f"Total returned: {result.get('total_returned')}")
    for i, hit in enumerate(result.get('hits', []), 1):
        print(f"  {i}. {hit.get('ELI')}")
        print(f"     Year: {hit.get('year')}, Status: {hit.get('status')}")
    return result


def main():
    print("=" * 60)
    print("ELI Acts Query Integration Tests")
    print("=" * 60)
    
    try:
        # Test eli_acts_query directly
        test_eli_acts_query_basic()
        test_eli_acts_query_year_filter()
        test_eli_acts_query_publisher_filter()
        test_eli_acts_query_keyword()
        test_combined_filters()
        
        # Test dataset discovery
        test_dataset_search_discovery()
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as exc:
        print(f"\n✗ Test failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
