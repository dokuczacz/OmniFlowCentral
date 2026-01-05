"""
Test eli_acts_query through the tools_call HTTP endpoint.

This simulates how a Custom GPT would call the tool.
"""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Mock HttpRequest for testing
class MockHttpRequest:
    def __init__(self, body_dict):
        self.body_dict = body_dict
        self.params = {}
        self.headers = {}
    
    def get_body(self):
        return json.dumps(self.body_dict).encode('utf-8')
    
    def get_json(self):
        return self.body_dict


from OmniFlowCentral.tools_call import main as tools_call_main


def test_eli_acts_query_via_http():
    """Test calling eli_acts_query through the HTTP endpoint"""
    print("\n=== Test: eli_acts_query via HTTP endpoint ===")
    
    # Simulate a Custom GPT request
    request_payload = {
        "tool": "eli_acts_query",
        "payload": {
            "params": {
                "q": "ustaw",
                "year": 2025,
                "limit": 3
            }
        }
    }
    
    mock_req = MockHttpRequest(request_payload)
    response = tools_call_main(mock_req)
    
    print(f"Status code: {response.status_code}")
    
    # Parse response
    response_data = json.loads(response.get_body().decode('utf-8'))
    print(f"Response status: {response_data.get('status')}")
    print(f"Tool: {response_data.get('tool')}")
    
    if response_data.get('status') == 'success':
        result = response_data.get('result', {})
        print(f"\nDataset: {result.get('dataset')}")
        print(f"Total returned: {result.get('total_returned')}")
        print(f"Hits:")
        for i, hit in enumerate(result.get('hits', []), 1):
            print(f"  {i}. {hit.get('ELI')} ({hit.get('year')})")
            print(f"     {hit.get('title')[:60]}...")
        print(f"\nProvenance: {result.get('provenance')}")
        return True
    else:
        print(f"ERROR: {response_data}")
        return False


def test_dataset_search_via_http():
    """Test discovering ELI dataset via dataset_search endpoint"""
    print("\n=== Test: dataset_search for ELI via HTTP endpoint ===")
    
    request_payload = {
        "tool": "dataset_search",
        "payload": {
            "user_id": "public",
            "params": {
                "tags_any": ["eli"],
                "category": "dataset",
                "limit": 5
            }
        }
    }
    
    mock_req = MockHttpRequest(request_payload)
    response = tools_call_main(mock_req)
    
    print(f"Status code: {response.status_code}")
    
    response_data = json.loads(response.get_body().decode('utf-8'))
    print(f"Response status: {response_data.get('status')}")
    
    if response_data.get('status') == 'success':
        result = response_data.get('result', {})
        print(f"Total hits: {result.get('total')}")
        
        for hit in result.get('hits', []):
            if 'eli' in hit.get('tags', []):
                print(f"\nFound ELI dataset:")
                print(f"  Name: {hit.get('display_name')}")
                print(f"  Tool: {hit.get('metadata', {}).get('tool')}")
                print(f"  Records: {hit.get('metadata', {}).get('record_count')}")
        return True
    else:
        print(f"ERROR: {response_data}")
        return False


def test_tools_capabilities():
    """Test that eli_acts_query appears in capabilities"""
    print("\n=== Test: Check capabilities endpoint ===")
    
    from OmniFlowCentral.tools_capabilities import main as capabilities_main
    
    mock_req = MockHttpRequest({})
    response = capabilities_main(mock_req)
    
    print(f"Status code: {response.status_code}")
    
    response_data = json.loads(response.get_body().decode('utf-8'))
    capabilities = response_data.get('capabilities', [])
    
    print(f"Total capabilities: {len(capabilities)}")
    
    # Find eli_acts_query
    eli_cap = None
    for cap in capabilities:
        if cap.get('name') == 'eli_acts_query':
            eli_cap = cap
            break
    
    if eli_cap:
        print(f"\n✓ Found eli_acts_query capability:")
        print(f"  Description: {eli_cap.get('description')}")
        print(f"  Method: {eli_cap.get('method')}")
        print(f"  Params: {json.dumps(eli_cap.get('params', {}), indent=4)}")
        return True
    else:
        print(f"\n✗ eli_acts_query NOT found in capabilities")
        return False


def main():
    print("=" * 70)
    print("ELI Acts Query - HTTP Endpoint Tests")
    print("=" * 70)
    
    results = []
    
    try:
        results.append(("Capabilities", test_tools_capabilities()))
        results.append(("Dataset Search", test_dataset_search_via_http()))
        results.append(("ELI Acts Query", test_eli_acts_query_via_http()))
        
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
