import json
import requests

import os

# Load URLs from environment or use placeholders to avoid committing secrets.
CAP_URL = os.environ.get(
    "OMNIFLOW_CAP_URL",
    "https://omniflowcentral-bagkbfera7d0hncc.switzerlandnorth-01.azurewebsites.net/api/tools/capabilities?code=REDACTED",
)
CALL_URL = os.environ.get(
    "OMNIFLOW_CALL_URL",
    "https://omniflowcentral-bagkbfera7d0hncc.switzerlandnorth-01.azurewebsites.net/api/tools/call?code=REDACTED",
)

headers = {"Content-Type": "application/json"}

def dump(r):
    print('status:', r.status_code)
    print('headers:')
    for k,v in r.headers.items():
        print('  ', k+':', v)
    print('body (repr):')
    print(repr(r.text))
    print('body length:', len(r.content))
    print('-'*60)

print('GET capabilities')
try:
    r = requests.get(CAP_URL, headers=headers, timeout=30)
    dump(r)
    try:
        print('json:', json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print('json decode error:', e)
except Exception as e:
    print('ERROR capabilities:', str(e))

print('\nPOST dataset_search')
ds_payload = {"tool": "dataset_search", "payload": {"user_id": "public", "params": {"tags_any": ["eli"], "category": "dataset", "limit": 5}}}
try:
    r = requests.post(CALL_URL, headers=headers, data=json.dumps(ds_payload), timeout=60)
    dump(r)
except Exception as e:
    print('ERROR dataset_search:', str(e))

print('\nPOST eli_acts_query')
q_payload = {"tool": "eli_acts_query", "payload": {"params": {"limit": 5}}}
try:
    r = requests.post(CALL_URL, headers=headers, data=json.dumps(q_payload), timeout=60)
    dump(r)
except Exception as e:
    print('ERROR eli_acts_query:', str(e))
