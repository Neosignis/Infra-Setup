"""Fixtures exercise plumbing only and are never installed as engine providers."""
import unittest

from fastapi.testclient import TestClient

from neosignis.api import create_app
from neosignis.auth import Settings
from neosignis.contracts import Capabilities, Capability, RecognizeResult
from neosignis.worker import create_app as create_worker

from test_contracts import utterance

TOKEN = "test-only-secret-" + "x" * 32
SETTINGS = Settings("local", "dev_token", TOKEN, "", "", "http://127.0.0.1:8001")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


class TransportFixture:
    def __init__(self, status=503, result=None):
        self.status, self.result = status, result
        self.calls = 0

    def call(self, path, payload=None):
        self.calls += 1
        return self.status, self.result


class ProviderFixture:
    def capabilities(self):
        return Capabilities(languages=[Capability(language="ase", recognize=True, approved=True, model_version="test-fixture", scope="unit-test-only")])

    def recognize(self, request):
        return RecognizeResult(language="ase", status="abstained", model_version="test-fixture", reason="unit-test-only")

    def render(self, request):
        raise AssertionError("Disabled renderer must not be called")


class GatewayTests(unittest.TestCase):
    def test_auth_rejects_without_contacting_worker(self):
        transport = TransportFixture()
        with TestClient(create_app(SETTINGS, transport)) as client:
            for headers in ({}, {"Authorization": "Bearer invalid"}):
                response = client.get("/v1/capabilities", headers=headers)
                self.assertEqual(response.status_code, 401)
            self.assertEqual(transport.calls, 0)

    def test_health_is_not_engine_readiness(self):
        with TestClient(create_app(SETTINGS, TransportFixture())) as client:
            self.assertEqual(client.get("/healthz").status_code, 200)
            self.assertEqual(client.get("/readyz").status_code, 503)

    def test_missing_model_produces_no_text(self):
        with TestClient(create_app(SETTINGS, TransportFixture())) as client:
            response = client.post("/v1/recognize", json=utterance(), headers=HEADERS)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("text", response.json())

    def test_input_error_does_not_echo_content(self):
        with TestClient(create_app(SETTINGS, TransportFixture())) as client:
            response = client.post("/v1/render", json={"text": "private-input", "signer_id": "invalid/", "language": "ase"}, headers=HEADERS)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("private-input", response.text)

    def test_actual_body_bytes_are_limited(self):
        with TestClient(create_app(SETTINGS, TransportFixture())) as client:
            response = client.post("/v1/recognize", content=b"x" * (4 * 1024 * 1024 + 1), headers=HEADERS)
            self.assertEqual(response.status_code, 413)

    def test_chunked_body_is_limited(self):
        with TestClient(create_app(SETTINGS, TransportFixture())) as client:
            chunks = (b"x" * (1024 * 1024) for _ in range(5))
            response = client.post("/v1/recognize", content=chunks, headers=HEADERS)
            self.assertEqual(response.status_code, 413)

    def test_malformed_output_rejected(self):
        with TestClient(create_app(SETTINGS, TransportFixture(200, {"text": "untrusted"}))) as client:
            response = client.post("/v1/recognize", json=utterance(), headers=HEADERS)
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("untrusted", response.text)

    def test_cross_language_output_rejected(self):
        output = {"language": "nsi", "status": "final", "text": "test-only", "model_version": "fixture"}
        with TestClient(create_app(SETTINGS, TransportFixture(200, output))) as client:
            self.assertEqual(client.post("/v1/recognize", json=utterance(), headers=HEADERS).status_code, 502)

    def test_cross_signer_render_rejected(self):
        output = {"language": "ase", "signer_id": "wrong", "renderer_version": "fixture", "status": "ready", "asset_id": "fixture", "output_kind": "recorded_signer"}
        with TestClient(create_app(SETTINGS, TransportFixture(200, output))) as client:
            response = client.post("/v1/render", json={"language": "ase", "signer_id": "expected", "text": "test-only"}, headers=HEADERS)
            self.assertEqual(response.status_code, 502)


class WorkerTests(unittest.TestCase):
    def test_default_worker_has_no_capabilities(self):
        with TestClient(create_worker()) as client:
            self.assertEqual(client.get("/healthz").status_code, 200)
            self.assertEqual(client.get("/readyz").status_code, 503)
            capabilities = client.get("/v1/capabilities").json()["languages"]
            self.assertFalse(any(c["recognize"] or c["render"] for c in capabilities))
            self.assertEqual(client.post("/v1/recognize", json=utterance()).status_code, 503)

    def test_nsl_cannot_fall_through_to_asl(self):
        with TestClient(create_worker(ProviderFixture())) as client:
            self.assertEqual(client.post("/v1/recognize", json=utterance("nsi")).status_code, 503)

    def test_valid_abstention_passes(self):
        with TestClient(create_worker(ProviderFixture())) as client:
            response = client.post("/v1/recognize", json=utterance())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "abstained")
            self.assertIsNone(response.json()["text"])

    def test_provider_version_mismatch_rejected(self):
        provider = ProviderFixture()
        provider.recognize = lambda request: RecognizeResult(language="ase", status="final", text="test-only", model_version="wrong-version")
        with TestClient(create_worker(provider)) as client:
            self.assertEqual(client.post("/v1/recognize", json=utterance()).status_code, 502)

    def test_busy_worker_rejects(self):
        app = create_worker(ProviderFixture())
        with TestClient(app) as client:
            app.state.busy = True
            self.assertEqual(client.post("/v1/recognize", json=utterance()).status_code, 429)
