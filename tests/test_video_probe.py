import importlib.util
import io
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

spec = importlib.util.spec_from_file_location('video_probe', Path(__file__).resolve().parents[1] / 'scripts/data/probe_how2sign.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
HAS_AV = importlib.util.find_spec('av') is not None


class SamplingTests(unittest.TestCase):
    def test_sample_is_stable_includes_extremes_and_excludes_missing_video(self):
        refs = {str(i): {'START': '0', 'END': str(i + 1)} for i in range(10)}
        available = set(refs) - {'9'}
        first = probe.select_names(refs, available, 4)
        second = probe.select_names(dict(reversed(list(refs.items()))), available, 4)
        self.assertEqual(first, second)
        self.assertIn('0', first)
        self.assertIn('8', first)
        self.assertNotIn('9', first)
        self.assertEqual(len(first), 4)

    def test_invalid_sample_bounds_and_no_matching_ids(self):
        for count in (0, 65):
            with self.assertRaises(ValueError):
                probe.select_names({}, set(), count)
        with self.assertRaisesRegex(ValueError, 'No matching'):
            probe.select_names({}, set(), 1)

    def test_nonfinite_or_negative_reference_duration_rejected(self):
        for duration in ('nan', '-1', '0'):
            with self.assertRaises(ValueError):
                probe.select_names({'x': {'START': '0', 'END': duration}}, {'x'}, 1)


@unittest.skipUnless(HAS_AV, 'Install requirements-data.txt to run real decoder tests')
class DecoderTests(unittest.TestCase):
    def fixture(self):
        import av
        output = io.BytesIO()
        with av.open(output, 'w', format='mp4') as container:
            stream = container.add_stream('mpeg4', rate=10)
            stream.width, stream.height, stream.pix_fmt = 32, 32, 'yuv420p'
            for index in range(8):
                frame = av.VideoFrame(32, 32, 'rgb24')
                frame.planes[0].update(bytes([index * 20]) * frame.planes[0].buffer_size)
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        return output.getvalue()

    def test_real_mp4_fully_decodes_with_timestamps_and_rgb_conversion(self):
        result = probe.decode_video_bytes(self.fixture())
        self.assertTrue(result['full_clip_decode_completed'])
        self.assertEqual(result['decoded_frames'], 8)
        self.assertEqual((result['width'], result['height']), (32, 32))
        self.assertEqual(result['fps_metadata'], 10)
        self.assertEqual(result['missing_timestamps'], 0)
        self.assertEqual(result['nonincreasing_timestamps'], 0)
        self.assertTrue(result['first_frame_rgb24_conversion_checked'])

    def test_decode_limit_does_not_report_partial_clip_as_complete(self):
        with self.assertRaisesRegex(ValueError, 'full decode was not completed'):
            probe.decode_video_bytes(self.fixture(), max_frames=3)

    def test_byte_bounds_and_empty_input_rejected(self):
        for payload in (b'', self.fixture()):
            with self.assertRaises(ValueError):
                probe.decode_video_bytes(payload, max_bytes=1)

    def test_invalid_container_is_rejected(self):
        import av
        with self.assertRaises(av.error.FFmpegError):
            probe.decode_video_bytes(b'This is not an MP4 container')

    def test_changed_source_is_rejected_before_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive, inventory = root / 'source.zip', root / 'inventory.json'
            archive.write_bytes(b'changed-source')
            inventory.write_text(json.dumps({'archive_sha256': '0' * 64}))
            with self.assertRaisesRegex(ValueError, 'changed since integrity'):
                probe.probe_dataset(archive, inventory, root / 'absent-references.csv')

    def test_zip_to_reference_decode_integration_keeps_source_unchanged(self):
        payload = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive, inventory, references = root / 'source.zip', root / 'inventory.json', root / 'refs.csv'
            with ZipFile(archive, 'w') as output:
                output.writestr('raw_videos/clip-rgb_front.mp4', payload)
            before = hashlib.sha256(archive.read_bytes()).hexdigest()
            inventory.write_text(json.dumps({'archive_sha256': before, 'mp4_files': 1,
                'entries': [{'path': 'raw_videos/clip-rgb_front.mp4', 'bytes': len(payload),
                             'sha256': hashlib.sha256(payload).hexdigest(), 'is_mp4': True}]}))
            with references.open('w', newline='') as output:
                writer = csv.DictWriter(output, fieldnames=['SENTENCE_NAME', 'START', 'END'], delimiter='\t')
                writer.writeheader()
                writer.writerow({'SENTENCE_NAME': 'clip-rgb_front', 'START': 0, 'END': .8})
                writer.writerow({'SENTENCE_NAME': 'missing-video', 'START': 0, 'END': 1})
            result = probe.probe_dataset(archive, inventory, references, sample_size=2)
            self.assertEqual(result['sampled_clips'], 1)
            self.assertEqual(result['fully_decoded_clips'], 1)
            self.assertFalse(result['training_approved'])
            self.assertFalse(result['linguistic_review_completed'])
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), before)


if __name__ == '__main__':
    unittest.main()
