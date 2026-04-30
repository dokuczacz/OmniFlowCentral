#!/usr/bin/env python3
"""
Diagnostic script to test SAOS API connectivity from different environments.
Helps identify networking issues and validate fixes.
"""

import json
import sys
import requests
from datetime import datetime

def test_local_saos():
    """Test SAOS API from local environment (should work)."""
    print("\n" + "="*60)
    print("Testing SAOS API from LOCAL environment")
    print("="*60)
    
    try:
        url = "https://www.saos.org.pl/api/search/judgments"
        params = {
            "pageSize": 1,
            "pageNumber": 0,
            "sortingField": "JUDGMENT_DATE",
            "sortingDirection": "DESC",
            "all": "test"
        }
        r = requests.get(url, params=params, timeout=10)
        print(f"✅ Status: {r.status_code}")
        print(f"✅ Response size: {len(r.text)} bytes")
        data = r.json()
        print(f"✅ Items returned: {len(data.get('items', []))}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_azure_saos():
    """Test SAOS API through Azure backend (may fail if networking restricted)."""
    print("\n" + "="*60)
    print("Testing SAOS API through AZURE backend")
    print("="*60)
    
    import os
    call_url = os.environ.get("OMNIFLOW_CALL_URL", "")
    if not call_url:
        print("⚠️  OMNIFLOW_CALL_URL not set. Skipping Azure backend test.")
        return None
    
    try:
        payload = {
            "tool": "saos_search",
            "payload": {
                "q": "konstytucja",
                "limit": 3
            }
        }
        r = requests.post(call_url, json=payload, timeout=30)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                hits = data.get("result", {}).get("hits", [])
                print(f"✅ Success! Retrieved {len(hits)} judgments")
                return True
            else:
                print(f"❌ API error: {data.get('code')}")
                print(f"   Message: {data.get('message')}")
                if data.get("details"):
                    print(f"   Details: {json.dumps(data['details'], indent=6)}")
                return False
        else:
            print(f"❌ HTTP {r.status_code}")
            print(r.text[:500])
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def diagnose_network_issue():
    """Diagnose the networking issue."""
    print("\n" + "="*60)
    print("Network Diagnostics")
    print("="*60)
    
    import socket
    
    # Check DNS resolution
    try:
        ip = socket.gethostbyname("www.saos.org.pl")
        print(f"✅ DNS Resolution: www.saos.org.pl -> {ip}")
    except Exception as e:
        print(f"❌ DNS Resolution failed: {e}")
        return
    
    # Check port connectivity
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, 443))
        sock.close()
        if result == 0:
            print(f"✅ Port 443 reachable from local: YES")
        else:
            print(f"❌ Port 443 reachable from local: NO (errno={result})")
    except Exception as e:
        print(f"⚠️  Port check error: {e}")

def main():
    print("\n" + "="*70)
    print(f"OmniFlowCentral SAOS Connectivity Diagnostic")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*70)
    
    local_ok = test_local_saos()
    azure_ok = test_azure_saos()
    
    diagnose_network_issue()
    
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    
    if local_ok and azure_ok is False:
        print("\n⚠️  FINDING: SAOS API works locally but NOT from Azure backend")
        print("\nRoot Cause: Azure Function App on FlexConsumption plan cannot")
        print("            reach external APIs (network isolation)")
        print("\nSolution: See AZURE_NETWORKING_FIX.md for remediation options")
        print("          Recommended: Upgrade to Standard plan or implement NAT Gateway")
        sys.exit(1)
    elif local_ok and azure_ok:
        print("\n✅ All tests passed! SAOS connectivity working.")
        sys.exit(0)
    elif not local_ok:
        print("\n❌ Local connectivity failed. Check your internet connection.")
        sys.exit(2)
    else:
        print("\n⚠️  Inconclusive test results.")
        sys.exit(1)

if __name__ == "__main__":
    main()
