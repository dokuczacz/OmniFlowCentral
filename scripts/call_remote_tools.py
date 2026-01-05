import json
import sys

import requests

import os

# Load URLs (with function keys) from environment for safety. If not set,
# use placeholder URLs without secrets so this file can be committed.
CAP_URL = os.environ.get(
    "OMNIFLOW_CAP_URL",
    "https://omniflowcentral-bagkbfera7d0hncc.switzerlandnorth-01.azurewebsites.net/api/tools/capabilities?code=REDACTED",
)
CALL_URL = os.environ.get(
    "OMNIFLOW_CALL_URL",
    "https://omniflowcentral-bagkbfera7d0hncc.switzerlandnorth-01.azurewebsites.net/api/tools/call?code=REDACTED",
)

headers = {"Content-Type": "application/json"}

try:
    r = requests.get(CAP_URL, headers=headers, timeout=30)
    print("=== capabilities response ===")
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(f"Status: {r.status_code}")
        print(r.text)
except Exception as e:
    print("ERROR capabilities:", str(e))

print('\n---\n')

ds_payload = {"tool": "dataset_search", "payload": {"user_id": "public", "params": {"tags_any": ["eli"], "category": "dataset", "limit": 5}}}
try:
    r = requests.post(CALL_URL, headers=headers, data=json.dumps(ds_payload), timeout=60)
    print("=== dataset_search response ===")
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(f"Status: {r.status_code}")
        print(r.text)
except Exception as e:
    print("ERROR dataset_search:", str(e))

print('\n---\n')

q_payload = {"tool": "eli_acts_query", "payload": {"params": {"limit": 5}}}
try:
    r = requests.post(CALL_URL, headers=headers, data=json.dumps(q_payload), timeout=60)
    print("=== eli_acts_query response ===")
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(f"Status: {r.status_code}")
        print(r.text)
except Exception as e:
    print("ERROR eli_acts_query:", str(e))

