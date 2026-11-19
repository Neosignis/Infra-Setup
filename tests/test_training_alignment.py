"""Synthetic media verifies diagnostic alignment mechanics, not ASL meaning."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from neosignis.training.alignment import compare_poses, inspect_video, make_review_video
from neosignis.training.prepared import IndexedPoseUtterance


def pose(frames=4):
    raw = np.full((frames, 133, 3), .5, dtype=np.float32)
    raw[:, :, 2] = 1.1
    raw[:, 5, 0], raw[:, 6, 0] = .3, .7
    return IndexedPoseUtterance('review-fixture', 'Unreviewed example.', 'train', raw.reshape(frames, 399),
                                 np.ones((frames, 399), dtype=np.bool_), np.arange(frames, dtype=np.int64))


class PoseDiagnosticTests(unittest.TestCase):
    def test_same_pose_is_zero_disagreement_not_language_approval(self):
        sample = pose()
        result = compare_poses(sample.features[0], sample.features[0], 320, 240)
        for part in result.values(): self.assertEqual(part['median_distance_image_diagonal'], 0)
        self.assertEqual(result['left_hand']['jointly_visible'], 21)

    def test_distance_is_scaled_by_actual_image_diagonal(self):
        a = pose().features[0].reshape(133, 3); b = a.copy(); b[:, 0] += 20 / 320
        result = compare_poses(a, b, 320, 240)
        self.assertAlmostEqual(result['body']['median_distance_image_diagonal'], 20 / 400, places=6)

    def test_missing_observations_are_unavailable_not_zero_error(self):
        a = pose().features[0]; b = np.zeros_like(a)
        result = compare_poses(a, b, 320, 240)
        self.assertIsNone(result['left_hand']['median_distance_image_diagonal'])
        self.assertEqual(result['left_hand']['jointly_visible'], 0)
        b[0] = np.nan
        with self.assertRaises(ValueError): compare_poses(a, b, 320, 240)


@unittest.skipUnless(importlib.util.find_spec('av') and importlib.util.find_spec('cv2'), 'Optional media review tests')
class ReviewMediaTests(unittest.TestCase):
    def source(self, root):
        import av
        from fractions import Fraction
        path = Path(root) / 'source.mp4'
        with av.open(path, 'w') as container:
            stream = container.add_stream('libx264', rate=25)
            stream.width, stream.height, stream.pix_fmt = 160, 120, 'yuv420p'
            stream.codec_context.time_base = Fraction(1, 1000)
            for stamp in (0, 40, 100, 160):
                frame = av.VideoFrame.from_ndarray(np.full((120, 160, 3), 80, dtype=np.uint8), format='bgr24')
                frame.pts, frame.time_base = stamp, Fraction(1, 1000)
                for packet in stream.encode(frame): container.mux(packet)
            for packet in stream.encode(): container.mux(packet)
        return path

    def test_overlay_keeps_all_frames_irregular_pts_and_original_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.source(tmp); before = hashlib.sha256(path.read_bytes()).hexdigest()
            info = inspect_video(path)
            self.assertEqual(info['frames'], 4)
            result = make_review_video(path, pose(), Path(tmp) / 'review.mp4')
            np.testing.assert_allclose(inspect_video(Path(tmp) / 'review.mp4')['timestamps_ms'], info['timestamps_ms'], atol=.1)
            self.assertTrue(result['pose_frame_count_matches'])
            self.assertTrue(result['derived_frame_count_and_pts_checked'])
            self.assertFalse(result['video_pose_alignment_approved'])
            self.assertFalse(result['linguistic_review_completed'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
            self.assertTrue(Path(result['thumbnail']).is_file())

    def test_count_mismatch_is_flagged_without_cropping_source_or_inventing_poses(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.source(tmp)
            result = make_review_video(source, pose(3), Path(tmp) / 'review.mp4')
            self.assertEqual(result['frames'], 4)
            self.assertEqual(result['pose_frames'], 3)
            self.assertIn('source_pose_frame_count_differs', result['engineering_review_flags'])
            self.assertIn('stored_indices_do_not_cover_source_exactly', result['engineering_review_flags'])
            self.assertEqual(inspect_video(Path(tmp) / 'review.mp4')['frames'], 4)

    def test_decode_budget_and_source_overwrite_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.source(tmp)
            with self.assertRaisesRegex(ValueError, 'bounds'): inspect_video(source, max_frames=2)
            with self.assertRaisesRegex(ValueError, 'preserve'): make_review_video(source, pose(), source)


class ReviewPacketTests(unittest.TestCase):
    def cli(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/data/prepare_alignment_review.py'
        spec = importlib.util.spec_from_file_location('alignment_review_cli_test', path)
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        return cli

    def test_html_escapes_supplied_text_and_keeps_reference_inside_reveal(self):
        cli = self.cli()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'review.html'
            record = {'id': 'test', 'reference': '<script>untrusted</script>', 'review_flags': [],
                      'technical': {'frames': 4, 'pose_frames': 4}, 'thumbnail': 'thumb.jpg',
                      'source_video': 'source.mp4', 'review_video': 'review.mp4'}
            cli.write_review_page(path, [record])
            page = path.read_text()
            self.assertIn('&lt;script&gt;untrusted&lt;/script&gt;', page)
            self.assertNotIn('<script>untrusted</script>', page)
            self.assertIn('<summary>Show supplied English reference</summary>', page)
            self.assertNotIn('fetch(', page)
            self.assertIn('automatic_training_promotion:false', page)

    def test_changed_existing_source_is_rejected_before_network_access(self):
        cli = self.cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'source-clips').mkdir(); (root / 'source-clips/a.mp4').write_bytes(b'changed')
            receipt = {'repo': cli.REPO, 'revision': cli.REVISION,
                       'clips': [{'id': 'a', 'path': 'source-clips/a.mp4', 'sha256': 'a' * 64}]}
            (root / 'acquisition.json').write_text(json.dumps(receipt))
            with patch.object(cli.urllib.request, 'urlopen', side_effect=AssertionError('No network for checked local source')):
                with self.assertRaisesRegex(ValueError, 'differs'): cli.download_sources({'training_ids': ['a']}, root)

    def test_bundle_includes_only_declared_artifacts_and_verifies_crc(self):
        from zipfile import ZipFile
        cli = self.cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'packet'; root.mkdir()
            for name in ('README.txt', 'review.html', 'review-sheet.csv', 'contact-sheet.jpg', 'review-manifest.json', 'acquisition.json',
                         'source-clips/source.mp4', 'overlays/review.mp4', 'overlays/thumb.jpg'):
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'fixture bytes')
            (root / 'unrelated-private-note.txt').write_text('Do not bundle')
            records = [{'source_video': 'source-clips/source.mp4', 'review_video': 'overlays/review.mp4', 'thumbnail': 'overlays/thumb.jpg'}]
            result = cli.bundle_packet(root, records)
            self.assertTrue(result['zip_crc_checked'])
            self.assertEqual(result['files'], 9)
            with ZipFile(result['path']) as archive:
                self.assertNotIn('packet/unrelated-private-note.txt', archive.namelist())
                self.assertEqual(archive.read('packet/source-clips/source.mp4'), b'fixture bytes')


if __name__ == '__main__': unittest.main()
