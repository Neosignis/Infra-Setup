"""Smoke-test retry regressions without Docker or network access."""
import importlib.util
import io
import json
import unittest
from http.client import RemoteDisconnected
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

spec = importlib.util.spec_from_file_location(
    "compose_smoke_under_test", Path(__file__).resolve().parents[1] / "scripts" / "smoke_compose.py"
)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class Response(io.BytesIO):
    def __init__(self, payload, status=200):
        super().__init__(json.dumps(payload).encode())
        self.status = status


class SmokeRetryTests(unittest.TestCase):
    def probe(self, responses, **kwargs):
        opener = Mock()
        opener.open.side_effect = responses
        sleep = Mock()
        result = smoke.wait_for_json('/healthz', opener=opener, sleep=sleep, attempts=3, **kwargs)
        return result, opener, sleep

    def test_connection_reset_is_retried(self):
        result, opener, sleep = self.probe([ConnectionResetError(104, 'reset'), Response({'status': 'alive'})])
        self.assertEqual(result, {'status': 'alive'})
        self.assertEqual(opener.open.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_remote_disconnect_is_retried(self):
        result, _, _ = self.probe([RemoteDisconnected('closed'), Response({'status': 'alive'})])
        self.assertEqual(result['status'], 'alive')

    def test_connection_refusal_is_retried(self):
        result, _, _ = self.probe([URLError('refused'), Response({'status': 'alive'})])
        self.assertEqual(result['status'], 'alive')

    def test_timeout_is_retried(self):
        result, _, _ = self.probe([TimeoutError(), Response({'status': 'alive'})])
        self.assertEqual(result['status'], 'alive')

    def test_worker_startup_503_is_retried(self):
        unavailable = HTTPError('http://fixture', 503, 'unavailable', {}, io.BytesIO(b'{}'))
        result, _, _ = self.probe([unavailable, Response({'status': 'alive'})])
        self.assertEqual(result['status'], 'alive')

    def test_authentication_error_fails_immediately(self):
        denied = HTTPError('http://fixture', 401, 'denied', {}, io.BytesIO(b'{}'))
        opener, sleep = Mock(), Mock()
        opener.open.side_effect = denied
        with self.assertRaisesRegex(RuntimeError, 'received HTTP 401'):
            smoke.wait_for_json('/v1/capabilities', opener=opener, sleep=sleep)
        self.assertEqual(opener.open.call_count, 1)
        sleep.assert_not_called()

    def test_persistent_reset_still_fails(self):
        opener, sleep = Mock(), Mock()
        opener.open.side_effect = ConnectionResetError(104, 'reset')
        with self.assertRaisesRegex(RuntimeError, 'exhausted after 3 attempts'):
            smoke.wait_for_json('/healthz', attempts=3, opener=opener, sleep=sleep)
        self.assertEqual(opener.open.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_expected_503_is_not_treated_as_failure(self):
        unavailable = HTTPError('http://fixture', 503, 'unavailable', {}, io.BytesIO(b'{"error":{"code":"engine_unavailable"}}'))
        result, _, sleep = self.probe([unavailable], expected_status=503)
        self.assertEqual(result['error']['code'], 'engine_unavailable')
        sleep.assert_not_called()

    def test_malformed_json_is_not_hidden_by_retries(self):
        response = Response({})
        response.seek(0)
        response.truncate()
        response.write(b'invalid-json')
        response.seek(0)
        with self.assertRaises(json.JSONDecodeError):
            self.probe([response])

    def test_unexpected_ready_200_fails(self):
        with self.assertRaisesRegex(RuntimeError, 'received HTTP 200'):
            self.probe([Response({'status': 'ready'})], expected_status=503)

    def test_token_is_attached_to_authenticated_probe(self):
        _, opener, _ = self.probe([Response({})], token='test-only-token')
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-only-token')


if __name__ == '__main__':
    unittest.main()
