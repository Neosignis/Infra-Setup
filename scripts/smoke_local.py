"""Exercise real gateway→worker HTTP with no model; prints no token or content."""
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


def port():
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        return connection.getsockname()[1]


def main():
    root = Path(__file__).resolve().parents[1]
    api_port, worker_port = port(), port()
    while worker_port == api_port:
        worker_port = port()
    token = secrets.token_urlsafe(32)
    environment = os.environ | {
        'APP_ENV': 'local', 'AUTH_MODE': 'dev_token', 'DEV_API_TOKEN': token,
        'ENGINE_PROVIDER': '', 'INFERENCE_URL': f'http://127.0.0.1:{worker_port}',
        'PYTHONPATH': str(root / 'src'),
    }
    opener = build_opener(ProxyHandler({}))
    processes = []
    with tempfile.TemporaryFile() as output:
        try:
            for module, target_port in [('worker', worker_port), ('api', api_port)]:
                processes.append(subprocess.Popen(
                    [sys.executable, '-m', 'uvicorn', f'neosignis.{module}:app', '--host', '127.0.0.1', '--port', str(target_port), '--no-access-log'],
                    cwd=root, env=environment, stdout=output, stderr=output,
                ))
            base = f'http://127.0.0.1:{api_port}'
            for attempt in range(50):
                try:
                    with opener.open(base + '/healthz', timeout=1) as response:
                        assert response.status == 200
                    break
                except (URLError, TimeoutError):
                    if any(process.poll() is not None for process in processes) or attempt == 49:
                        raise RuntimeError('Service did not boot; inspect configuration/runtime') from None
                    time.sleep(0.1)
            request = Request(base + '/v1/capabilities', headers={'Authorization': 'Bearer ' + token})
            with opener.open(request, timeout=2) as response:
                capabilities = json.load(response)
            assert {c['language'] for c in capabilities['languages']} == {'ase', 'nsi'}
            assert not any(c['recognize'] or c['render'] for c in capabilities['languages'])
            for path, expected in [('/readyz', 503), ('/v1/capabilities', 401)]:
                try:
                    opener.open(base + path, timeout=2)
                except HTTPError as exc:
                    assert exc.code == expected, (path, exc.code)
                else:
                    raise AssertionError((path, 'unexpected success'))
            print('Live HTTP smoke passed: liveness=200; authenticated capabilities=disabled; readiness=503; unauthenticated=401')
        finally:
            for process in processes:
                process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    main()
