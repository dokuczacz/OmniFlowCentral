import json
import requests


def test_health(base_url):
    resp = requests.get(f"{base_url}/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"


def test_tools_capabilities(base_url):
    resp = requests.get(f"{base_url}/api/tools/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert "capabilities" in data
    names = [c.get("name") for c in data.get("capabilities", [])]
    assert "list_blobs" in names or "get_blob" in names
