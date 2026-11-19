import hashlib
import importlib.util
import io
from contextlib import redirect_stderr
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from zipfile import BadZipFile, ZipFile, ZipInfo, ZIP_DEFLATED

spec = importlib.util.spec_from_file_location(
    'source_inspector', Path(__file__).resolve().parents[1] / 'scripts/data/inspect_source_archive.py')
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


class SourceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'source.tar'

    def archive(self, names=('hello/signer--clip.mp4',), *, link=False, content=None):
        payload = b'\x00\x00\x00\x18ftypisom' if content is None else content
        with tarfile.open(self.path, 'w') as archive:
            for name in names:
                entry = tarfile.TarInfo(name)
                if link:
                    entry.type = tarfile.SYMTYPE
                    entry.linkname = '../../outside'
                    archive.addfile(entry)
                else:
                    entry.size = len(payload)
                    archive.addfile(entry, io.BytesIO(payload))
        return self.path

    def test_checks_bytes_without_claiming_decode_or_training_approval(self):
        self.archive()
        result = inspector.inspect_archive(self.path, expected_bytes=self.path.stat().st_size)
        self.assertEqual(result['mp4_files_with_ftyp'], 1)
        self.assertEqual(result['archive_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertFalse(result['training_approved'])
        self.assertFalse(result['video_decode_checked'])
        self.assertFalse((self.path.parent / 'hello').exists())

    def test_wrong_download_size_rejected(self):
        self.archive()
        with self.assertRaisesRegex(ValueError, 'size differs'):
            inspector.inspect_archive(self.path, expected_bytes=1)

    def test_archive_hash_mismatch_rejected(self):
        self.archive()
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            inspector.inspect_archive(self.path, expected_sha256='0' * 64)

    def test_traversal_absolute_and_windows_paths_rejected(self):
        for name in ('../outside.mp4', '/outside.mp4', 'C:/outside.mp4', 'a\\outside.mp4'):
            with self.subTest(name=name):
                self.archive((name,))
                with self.assertRaisesRegex(ValueError, 'unsafe path'):
                    inspector.inspect_archive(self.path)

    def test_symlinks_rejected(self):
        self.archive(link=True)
        with self.assertRaisesRegex(ValueError, 'link or special'):
            inspector.inspect_archive(self.path)

    def test_duplicate_normalized_paths_rejected(self):
        self.archive(('hello/clip.mp4', './hello/clip.mp4'))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            inspector.inspect_archive(self.path)

    def test_invalid_video_header_is_reported_not_called_decodable(self):
        self.archive(content=b'not-a-video')
        result = inspector.inspect_archive(self.path)
        self.assertEqual(result['mp4_files_with_ftyp'], 0)
        self.assertFalse(result['video_decode_checked'])

    def test_archive_and_member_count_bounds(self):
        self.archive(('a.mp4', 'b.mp4'))
        with self.assertRaisesRegex(ValueError, 'size bound'):
            inspector.inspect_archive(self.path, max_bytes=1)
        with self.assertRaisesRegex(ValueError, 'member-count'):
            inspector.inspect_archive(self.path, max_members=1)

    def test_truncated_file_payload_rejected(self):
        self.archive(content=b'x' * 2048)
        self.path.write_bytes(self.path.read_bytes()[:600])
        with self.assertRaises((ValueError, tarfile.TarError)):
            inspector.inspect_archive(self.path)

    def test_report_output_cannot_replace_archive(self):
        self.archive()
        before = self.path.read_bytes()
        with patch('sys.argv', ['inspect_source_archive.py', str(self.path), '--output', str(self.path)]):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(inspector.main(), 1)
        self.assertEqual(self.path.read_bytes(), before)


class SourceZipTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'source.zip'

    def archive(self, names=('video.mp4',), payload=b'\x00\x00\x00\x18ftypisom'):
        with ZipFile(self.path, 'w') as archive:
            for name in names:
                archive.writestr(name, payload)

    def test_valid_zip_checks_crc_without_extraction_or_language_claims(self):
        self.archive()
        result = inspector.inspect_zip_archive(self.path)
        self.assertEqual(result['files'], 1)
        self.assertEqual(result['mp4_files_with_ftyp'], 1)
        self.assertFalse(result['training_approved'])
        self.assertFalse(result['video_decode_checked'])
        self.assertFalse((self.path.parent / 'video.mp4').exists())

    def test_unsafe_paths_rejected(self):
        for name in ('../video.mp4', '/video.mp4', 'C:/video.mp4', 'a\\video.mp4'):
            with self.subTest(name=name):
                self.archive((name,))
                with self.assertRaisesRegex(ValueError, 'unsafe path'):
                    inspector.inspect_zip_archive(self.path)

    def test_symlink_rejected(self):
        entry = ZipInfo('video.mp4')
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        with ZipFile(self.path, 'w') as archive:
            archive.writestr(entry, '../outside')
        with self.assertRaisesRegex(ValueError, 'link or special'):
            inspector.inspect_zip_archive(self.path)

    def test_duplicate_normalized_path_rejected(self):
        self.archive(('video.mp4', './video.mp4'))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            inspector.inspect_zip_archive(self.path)

    def test_expansion_bound_checked_before_reading(self):
        with ZipFile(self.path, 'w', compression=ZIP_DEFLATED) as archive:
            archive.writestr('video.mp4', b'x' * 10000)
        with self.assertRaisesRegex(ValueError, 'oversized'):
            inspector.inspect_zip_archive(self.path, max_content_bytes=100)

    def test_corrupt_payload_crc_rejected(self):
        self.archive()
        data = bytearray(self.path.read_bytes())
        with ZipFile(self.path) as archive:
            entry = archive.infolist()[0]
            offset = entry.header_offset + 30 + len(entry.filename.encode()) + len(entry.extra)
        data[offset] ^= 1
        self.path.write_bytes(data)
        with self.assertRaises(BadZipFile):
            inspector.inspect_zip_archive(self.path)

    def test_download_size_hash_and_member_count_bounds(self):
        self.archive(('a.mp4', 'b.mp4'))
        with self.assertRaisesRegex(ValueError, 'size differs'):
            inspector.inspect_zip_archive(self.path, expected_bytes=1)
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            inspector.inspect_zip_archive(self.path, expected_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'member-count'):
            inspector.inspect_zip_archive(self.path, max_members=1)


if __name__ == '__main__':
    unittest.main()
