"""Checks container wiring, never translation quality; intended for Docker CI."""
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

for attempt in range(30):
    try:
        with urlopen('http://127.0.0.1:8000/healthz', timeout=2) as response:
            assert response.status == 200
        break
    except (URLError, TimeoutError):
        if attempt == 29:
            raise
        time.sleep(1)

request = Request('http://127.0.0.1:8000/v1/capabilities', headers={'Authorization': 'Bearer ' + os.environ['DEV_API_TOKEN']})
for attempt in range(30):
    try:
        with urlopen(request, timeout=2) as response:
            capabilities = json.load(response)
        assert not any(c['recognize'] or c['render'] for c in capabilities['languages'])
        break
    except HTTPError as exc:
        if exc.code != 503 or attempt == 29:
            raise
        time.sleep(1)
try:
    urlopen('http://127.0.0.1:8000/readyz', timeout=2)
except HTTPError as exc:
    assert exc.code == 503
else:
    raise AssertionError('Unconfigured model must not report ready')
print('Compose wiring passed; model readiness correctly unavailable')
