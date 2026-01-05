"""
Local script: discover ELI dataset via `dataset_search`, then call `eli_acts_query` via `tools_call` handler and print 5 hits.
"""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

class MockHttpRequest:
    def __init__(self, body_dict):
        self._body = body_dict
        self.headers = {}
        self.params = {}
    def get_body(self):
        return json.dumps(self._body).encode('utf-8')
    def get_json(self):
        return self._body

from OmniFlowCentral.tools_call import main as tools_call_main


def call_tool(tool, payload):
    req = MockHttpRequest({"tool": tool, "payload": payload})
    resp = tools_call_main(req)
    body = resp.get_body().decode('utf-8')
    return json.loads(body)


def main():
    print("Discovering ELI dataset via dataset_search...")
    ds_payload = {"user_id": "public", "params": {"tags_any": ["eli"], "category": "dataset", "limit": 5}}
    ds_resp = call_tool("dataset_search", ds_payload)
    print(json.dumps(ds_resp, indent=2, ensure_ascii=False))

    # Now call eli_acts_query for 5 items
    print("\nQuerying eli_acts_query for 5 items...")
    query_payload = {"params": {"limit": 5}}
    q_resp = call_tool("eli_acts_query", query_payload)
    print(json.dumps(q_resp, indent=2, ensure_ascii=False))

    hits = q_resp.get('result', {}).get('hits') if q_resp.get('status') == 'success' else q_resp.get('result', {}).get('hits', [])
    # Some handlers return result nested under 'result' by tools_call.success, adjust
    if not hits and isinstance(q_resp.get('result'), dict) and q_resp['result'].get('hits'):
        hits = q_resp['result']['hits']
    if not hits and q_resp.get('hits'):
        hits = q_resp['hits']

    print("\nExact 5 candidates:")
    for i, hit in enumerate(hits or [], 1):
        print(f"{i}. ELI: {hit.get('ELI')} | Title: {hit.get('title')[:120]} | Year: {hit.get('year')} | Publisher: {hit.get('publisher')} | Pos: {hit.get('pos')}")

if __name__ == '__main__':
    main()
