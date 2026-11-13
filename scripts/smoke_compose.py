"""Check Compose wiring with bounded startup retries; never test translation quality."""
import json
import os
import time
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

BASE_URL = "http://127.0.0.1:8000"


def wait_for_json(path, *, token=None, expected_status=200, attempts=60,
                  opener=None, sleep=time.sleep):
    """Retry startup transport failures/503; reject auth and contract errors."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    if opener is None:
        opener = build_opener(ProxyHandler({}))
    headers = {"Authorization": "Bearer " + token} if token else {}
    request = Request(BASE_URL + path, headers=headers)
    last_failure = "no response"
    for attempt in range(attempts):
        try:
            try:
                with opener.open(request, timeout=2) as response:
                    status = response.status
                    payload = json.load(response)
            except HTTPError as response:
                with response:
                    status = response.code
                    # Read only expected error responses; never print error bodies.
                    payload = json.load(response) if status == expected_status else None
            if status == expected_status:
                return payload
            if status != 503:
                raise RuntimeError(
                    f"{path}: expected HTTP {expected_status}, received HTTP {status}"
                )
            last_failure = "HTTP 503 (service unavailable)"
        except (URLError, ConnectionError, TimeoutError, IncompleteRead) as exc:
            # Includes ConnectionResetError and http.client.RemoteDisconnected.
            last_failure = type(exc).__name__
        if attempt + 1 < attempts:
            sleep(1)
    raise RuntimeError(
        f"{path}: startup checks exhausted after {attempts} attempts; "
        f"last failure: {last_failure}. Check the container logs printed by CI."
    ) from None


def main():
    token = os.environ.get("DEV_API_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("Set DEV_API_TOKEN to at least 32 characters for the CI smoke test")
    health = wait_for_json("/healthz")
    if health != {"status": "alive"}:
        raise RuntimeError("Unexpected API liveness response")
    capabilities = wait_for_json("/v1/capabilities", token=token)
    languages = capabilities["languages"]
    if len(languages) != 2 or {item["language"] for item in languages} != {"ase", "nsi"}:
        raise RuntimeError("Default worker must advertise ASL and NSL capability states")
    if any(item["recognize"] or item["render"] or item["approved"] for item in languages):
        raise RuntimeError("Foundation worker must not enable an unconfigured model")
    readiness = wait_for_json("/readyz", expected_status=503)
    if readiness["error"]["code"] != "engine_unavailable":
        raise RuntimeError("Unconfigured worker must report engine_unavailable")
    unauthorized = wait_for_json("/v1/capabilities", expected_status=401)
    if unauthorized["error"]["code"] != "unauthorized":
        raise RuntimeError("API must require authentication")
    print("Compose smoke passed: API alive; worker connected; capabilities disabled; readiness=503; authentication enforced")


if __name__ == "__main__":
    main()
