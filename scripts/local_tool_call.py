import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
APP_ROOT = REPO_ROOT / "OmniFlowCentral"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from OmniFlowCentral.tools_call import main as tools_call_main


class SimpleReq:
    def __init__(self, json_body=None, params=None, headers=None):
        self._json = json_body or {}
        self.params = params or {}
        self.headers = headers or {}

    def get_json(self):
        return self._json


payload = {
    "tool": "query_dataset",
    "dataset": "saos_judgments",
    "q": "Amber",
    "limit": 2,
    "fetch_content": True,
    "user_id": "default",
}

req = SimpleReq(json_body=payload, headers={"X-User-Id": "default"})
resp = tools_call_main(req)
body = json.loads(resp.get_body().decode("utf-8"))
print("status", resp.status_code)
print(json.dumps(body, ensure_ascii=False, indent=2))
