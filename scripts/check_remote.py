import requests

URL = 'https://omniflowcentral-bagkbfera7d0hncc.switzerlandnorth-01.azurewebsites.net/api/health'
try:
    r = requests.get(URL, timeout=10)
    print('status:', r.status_code)
    print('text:', r.text)
except Exception as e:
    print('error:', e)
