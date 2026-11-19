import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('asset_downloader', Path(__file__).resolve().parents[1] / 'scripts/data/download_unisign_assets.py')
downloader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(downloader)


class Response(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status, self.headers = status, headers or {}


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name) / 'weights.bin'
        self.payload = b'verified-weight-fixture'
        self.expected = {'max_bytes': 100, 'expected_bytes': len(self.payload),
                         'expected_sha': hashlib.sha256(self.payload).hexdigest()}

    def test_verified_download_publishes_complete_asset(self):
        with patch.object(downloader.urllib.request, 'urlopen', return_value=Response(self.payload)):
            result = downloader.download('https://example.invalid/model', self.destination, **self.expected)
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertEqual(result['sha256'], self.expected['expected_sha'])
        self.assertFalse(self.destination.with_name('weights.bin.part').exists())

    def test_resume_checks_content_range_and_keeps_full_hash(self):
        self.destination.with_name('weights.bin.part').write_bytes(self.payload[:5])
        response = Response(self.payload[5:], 206, {'Content-Range': f'bytes 5-{len(self.payload)-1}/{len(self.payload)}'})
        with patch.object(downloader.urllib.request, 'urlopen', return_value=response) as request:
            downloader.download('https://example.invalid/model', self.destination, **self.expected)
        self.assertEqual(request.call_args.args[0].headers['Range'], 'bytes=5-')
        self.assertEqual(self.destination.read_bytes(), self.payload)

    def test_ignored_range_restarts_instead_of_appending(self):
        self.destination.with_name('weights.bin.part').write_bytes(b'old')
        with patch.object(downloader.urllib.request, 'urlopen', return_value=Response(self.payload)):
            downloader.download('https://example.invalid/model', self.destination, **self.expected)
        self.assertEqual(self.destination.read_bytes(), self.payload)

    def test_bad_hash_never_publishes(self):
        with patch.object(downloader.urllib.request, 'urlopen', return_value=Response(b'changed')):
            with self.assertRaisesRegex(ValueError, 'verification failed'):
                downloader.download('https://example.invalid/model', self.destination, **self.expected)
        self.assertFalse(self.destination.exists())

    def test_changed_existing_asset_is_not_overwritten(self):
        self.destination.write_bytes(b'user-file')
        with self.assertRaisesRegex(ValueError, 'Existing asset differs'):
            downloader.download('https://example.invalid/model', self.destination, **self.expected)
        self.assertEqual(self.destination.read_bytes(), b'user-file')

    def test_oversized_response_rejected(self):
        with patch.object(downloader.urllib.request, 'urlopen', return_value=Response(b'x' * 101)):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                downloader.download('https://example.invalid/model', self.destination, **self.expected)


if __name__ == '__main__':
    unittest.main()
