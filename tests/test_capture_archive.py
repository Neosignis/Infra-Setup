import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from zipfile import ZipFile

spec = importlib.util.spec_from_file_location('capture_validator_under_test', Path(__file__).resolve().parents[1] / 'scripts/data/validate_capture.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class CaptureArchiveTests(unittest.TestCase):
    def setUp(self):
        self.video = b'test-fixture-not-real-signing'
        self.manifest = {'schema_version': 'neosignis.capture.v1', 'language': 'ase', 'training_authorized': False, 'rendering_authorized': False, 'clips': [{
            'id': 'fixture', 'signer_id': 'fixture-signer', 'permission_reference': 'fixture-permission',
            'local_recording_acknowledged': True, 'rights_review_status': 'unreviewed', 'split': 'unassigned',
            'expected_intent': 'E01', 'duration_ms': 1000, 'file': 'clips/fixture.webm',
            'bytes': len(self.video), 'sha256': hashlib.sha256(self.video).hexdigest(),
        }]}

    def archive(self, extra=None):
        output = io.BytesIO()
        with ZipFile(output, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(self.manifest))
            archive.writestr('clips/fixture.webm', self.video)
            if extra:
                archive.writestr(extra, 'unexpected')
        output.seek(0)
        return output

    def test_valid_integrity_never_claims_training_ready(self):
        result = validator.validate_archive(self.archive())
        self.assertEqual(result['clips'], 1)
        self.assertFalse(result['training_ready'])

    def test_checksum_corruption_rejected(self):
        self.manifest['clips'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'checksum'):
            validator.validate_archive(self.archive())

    def test_dataset_split_cannot_be_assigned_by_capture(self):
        self.manifest['clips'][0]['split'] = 'test'
        with self.assertRaises(ValueError):
            validator.validate_archive(self.archive())

    def test_likeness_or_training_permission_cannot_be_inferred(self):
        self.manifest['training_authorized'] = True
        with self.assertRaises(ValueError):
            validator.validate_archive(self.archive())

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unsafe path'):
            validator.validate_archive(self.archive('../outside.txt'))

    def test_missing_permission_reference_rejected(self):
        self.manifest['clips'][0]['permission_reference'] = ''
        with self.assertRaises(ValueError):
            validator.validate_archive(self.archive())

    def test_oversized_duration_rejected(self):
        self.manifest['clips'][0]['duration_ms'] = 10_001
        with self.assertRaises(ValueError):
            validator.validate_archive(self.archive())
