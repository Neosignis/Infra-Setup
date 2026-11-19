"""Synthetic media checks mechanics, never ASL accuracy."""
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

import numpy as np

from neosignis.training.how2sign import FeatureDataset, How2SignArchive
from neosignis.training.utterances import (
    LengthBucketSampler, Utterance, collate_utterances, torch_collate_utterances,
)


def utterance(name='a', length=4, split='train', width=3):
    return Utterance(name, 'Please repeat that.', split,
                     np.arange(length * width, dtype=np.float32).reshape(length, width),
                     np.ones((length, width), dtype=np.bool_),
                     np.arange(length, dtype=np.float64) * 100, 'test.features.v1', 'synthetic.v1')


class BatchTests(unittest.TestCase):
    def test_long_utterance_keeps_every_frame_and_whole_text(self):
        long, short = utterance('long', 534), utterance('short', 23)
        batch = collate_utterances([long, short])
        self.assertEqual(batch['features'].shape, (2, 534, 3))
        self.assertEqual(batch['lengths'].tolist(), [534, 23])
        np.testing.assert_array_equal(batch['features'][0], long.features)
        self.assertEqual(batch['timestamps_ms'][0, -1], 53300)
        self.assertEqual(batch['texts'], [long.text, short.text])
        self.assertTrue(batch['frame_mask'][1, :23].all())
        self.assertFalse(batch['frame_mask'][1, 23:].any())

    def test_missing_observation_is_not_temporal_padding(self):
        sample = utterance()
        sample.observed[1, 0] = False
        batch = collate_utterances([sample])
        self.assertTrue(batch['frame_mask'][0, 1])
        self.assertFalse(batch['observed'][0, 1, 0])
        self.assertEqual(batch['features'][0, 1, 0], 0)

    def test_invalid_times_nonfinite_features_and_masks_rejected(self):
        for problem in ('times', 'nan', 'mask'):
            sample = utterance()
            if problem == 'times':
                sample.timestamps_ms[2] = sample.timestamps_ms[1]
            elif problem == 'nan':
                sample.features[0, 0] = np.nan
            else:
                object.__setattr__(sample, 'observed', np.ones((4, 3), dtype=np.int64))
            with self.assertRaises(ValueError):
                collate_utterances([sample])

    def test_split_layout_and_duplicate_id_mixing_rejected(self):
        for second in (utterance('b', split='val'), utterance('b', width=4), utterance('a')):
            with self.assertRaises(ValueError):
                collate_utterances([utterance(), second])
        second = utterance('b')
        object.__setattr__(second, 'extractor_version', 'different')
        with self.assertRaises(ValueError):
            collate_utterances([utterance(), second])

    def test_padding_budget_counts_padded_not_true_lengths(self):
        with self.assertRaisesRegex(ValueError, 'budget'):
            collate_utterances([utterance('a', 5), utterance('b', 2)], max_padded_frames=9)
        with self.assertRaisesRegex(ValueError, 'budget'):
            collate_utterances([utterance()], max_batch_bytes=1)
        with self.assertRaises(ValueError):
            collate_utterances([])

    def test_bucket_coverage_reproducibility_and_padding_bound(self):
        lengths = [1, 13, 800, 100, 110, 1200, 30, 1500, 1600]
        sampler = LengthBucketSampler(lengths, max_batch_size=3, max_padded_frames=3200, seed=7)
        first = list(sampler)
        self.assertEqual(first, list(sampler))
        self.assertEqual(sorted(i for group in first for i in group), list(range(len(lengths))))
        self.assertEqual(len(first), len(sampler))
        for group in first:
            self.assertLessEqual(len(group) * max(lengths[i] for i in group), 3200)
        sampler.set_epoch(2)
        self.assertEqual(sorted(i for g in sampler for i in g), list(range(len(lengths))))

    def test_bucket_rejects_oversize_instead_of_dropping(self):
        for lengths in ([7201], [0], [], [True], [3.5]):
            with self.assertRaises(ValueError):
                LengthBucketSampler(lengths)
        # Feature caches commonly expose lengths as a NumPy vector.
        self.assertEqual(list(LengthBucketSampler(np.array([4, 8]), shuffle=False)), [[0, 1]])

    def test_complete_target_tokens_and_loss_padding(self):
        # Local fixture vocabulary; this is not a trained ASL tokenizer.
        def encode(text):
            return [len(word) for word in text.split()] + [1]
        first, second = utterance('a'), utterance('b')
        object.__setattr__(second, 'text', 'Hello.')
        batch = collate_utterances([first, second], encode_text=encode)
        self.assertEqual(batch['labels'].tolist(), [[6, 6, 5, 1], [6, 1, -100, -100]])
        self.assertEqual(batch['target_mask'].tolist(), [[True] * 4, [True, True, False, False]])

    def test_oversized_or_invalid_targets_reject_without_clipping(self):
        for encode in (lambda text: range(513), lambda text: [], lambda text: [-1], lambda text: [True]):
            with self.assertRaisesRegex(ValueError, 'target tokens'):
                collate_utterances([utterance()], encode_text=encode)

    def test_irregular_timestamps_are_preserved(self):
        sample = utterance()
        sample.timestamps_ms[:] = [0, 16.6, 50, 83.4]
        np.testing.assert_array_equal(collate_utterances([sample])['timestamps_ms'][0], sample.timestamps_ms)

    @unittest.skipUnless(importlib.util.find_spec('torch'), 'Optional torch adapter; tested in training environment')
    def test_real_pytorch_dataloader_preserves_lengths(self):
        import torch
        from torch.utils.data import DataLoader
        samples = [utterance('a', 500), utterance('b', 12)]
        batch = next(iter(DataLoader(samples, batch_size=2, collate_fn=torch_collate_utterances)))
        self.assertEqual(batch['features'].dtype, torch.float32)
        self.assertEqual(batch['frame_mask'].dtype, torch.bool)
        self.assertEqual(batch['lengths'].tolist(), [500, 12])
        self.assertEqual(batch['features'][0, -1, -1], samples[0].features[-1, -1])


@unittest.skipUnless(importlib.util.find_spec('av'), 'Install requirements-data.txt for real MP4 tests')
class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive, self.inventory, self.refs = [self.root / n for n in ('source.zip', 'inventory.json', 'refs.csv')]
        import av
        payload = io.BytesIO()
        with av.open(payload, 'w', format='mp4') as container:
            stream = container.add_stream('mpeg4', rate=25)
            stream.width, stream.height, stream.pix_fmt = 32, 32, 'yuv420p'
            for index in range(351):  # 14 seconds and >300 frames
                frame = av.VideoFrame(32, 32, 'rgb24')
                frame.planes[0].update(bytes([index % 256]) * frame.planes[0].buffer_size)
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        data = payload.getvalue()
        with ZipFile(self.archive, 'w') as archive:
            archive.writestr('raw_videos/example-rgb_front.mp4', data)
        self.before = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.entry = {'path': 'raw_videos/example-rgb_front.mp4', 'bytes': len(data),
                      'sha256': hashlib.sha256(data).hexdigest(), 'is_mp4': True}
        self.write_inventory()
        with self.refs.open('w', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=['SENTENCE_NAME', 'START', 'END', 'SENTENCE'], delimiter='\t')
            writer.writeheader()
            # Source START must NOT cause a second crop inside sentence clip.
            writer.writerow({'SENTENCE_NAME': 'example-rgb_front', 'START': 30, 'END': 44.04, 'SENTENCE': 'Complete sentence.'})
            writer.writerow({'SENTENCE_NAME': 'missing', 'START': 0, 'END': 1, 'SENTENCE': 'Missing video.'})

    def write_inventory(self):
        self.inventory.write_text(json.dumps({'archive_sha256': self.before, 'entries': [self.entry]}))

    def source(self, **kwargs):
        return How2SignArchive(self.archive, self.inventory, self.refs, split='val', **kwargs)

    @staticmethod
    def diagnostic_extractor(frame):
        # Dimension measurements only. Never passed off as ASL pose features.
        return [frame.width, frame.height], np.array([True, True])

    def test_whole_long_mp4_loads_lazily_with_original_pts_and_text(self):
        source = self.source()
        dataset = FeatureDataset(source, self.diagnostic_extractor,
                                 feature_schema='diagnostic.dimensions', extractor_version='test.v1')
        sample = dataset[0]
        self.assertEqual(len(dataset), 1)
        self.assertEqual(source.missing_video_ids, ['missing'])
        self.assertEqual(sample.features.shape, (351, 2))
        self.assertEqual(sample.timestamps_ms[0], 0)
        self.assertAlmostEqual(sample.timestamps_ms[-1], 14000)
        self.assertEqual(sample.text, 'Complete sentence.')
        self.assertEqual(sample.split, 'val')
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(), self.before)

    def test_full_sample_rejected_instead_of_silently_truncated(self):
        for bounds in ({'max_frames': 300}, {'max_duration_s': 10}, {'max_clip_bytes': 1}, {'max_feature_bytes': 1}):
            with self.assertRaisesRegex(ValueError, 'budget|oversized'):
                self.source(**bounds).load(0, self.diagnostic_extractor,
                                          feature_schema='test', extractor_version='test')

    def test_validation_cannot_be_used_for_training(self):
        with self.assertRaisesRegex(ValueError, 'publisher train split'):
            self.source(usage='training', approval_record_id='not-an-override')
        with self.assertRaisesRegex(ValueError, 'approval'):
            How2SignArchive(self.archive, self.inventory, self.refs, split='train', usage='training')

    def test_nonfinite_or_invalid_resource_bounds_rejected(self):
        for bounds in ({'max_duration_s': float('nan')}, {'max_frames': 0}, {'max_clip_bytes': True}):
            with self.assertRaisesRegex(ValueError, 'bounds'):
                self.source(**bounds)

    def test_changed_archive_and_member_hash_are_rejected(self):
        self.entry['sha256'] = '0' * 64
        self.write_inventory()
        with self.assertRaisesRegex(ValueError, 'Clip hash'):
            list(self.source().iter_frames(0))
        with self.archive.open('ab') as output:
            output.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'Source archive differs'):
            self.source()

    def test_bad_extractor_cannot_create_valid_features(self):
        for extractor in (lambda frame: ([np.nan], np.array([True])),
                          lambda frame: ([1.0], np.array([1]))):
            with self.assertRaises(ValueError):
                self.source().load(0, extractor, feature_schema='test', extractor_version='test')

    def test_unsafe_member_path_and_bad_reference_rejected(self):
        self.entry['path'] = '../escape.mp4'
        self.write_inventory()
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            self.source()
        self.entry['path'] = 'raw_videos/example-rgb_front.mp4'
        self.write_inventory()
        self.refs.write_text('SENTENCE_NAME\tSTART\tEND\tSENTENCE\nx\t0\tnan\tText\n')
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            self.source()


if __name__ == '__main__':
    unittest.main()
