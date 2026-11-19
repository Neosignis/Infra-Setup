"""Preparation mechanics only; synthetic poses never establish ASL accuracy."""
import gzip
import hashlib
import importlib.util
import io
import json
import pickle
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np

from neosignis.training.pose import POSE_SCHEMA, unisign_collate
from neosignis.training.prepared import (PreparedPoseDataset, convert_publisher_pose,
                                        load_publisher_labels, save_numeric, select_pilot, source_group)
from neosignis.training.utterances import Utterance
from neosignis.training.remote_zip import MultipartRangeReader


def numeric_pose(frames=20):
    coordinates = np.full((frames, 1, 133, 2), .5, dtype=np.float64)
    coordinates[:, :, 5, 0], coordinates[:, :, 6, 0] = .3, .7
    coordinates[:, :, 91:, 0] += np.sin(np.arange(frames) / 3)[:, None, None] * .1
    return {'keypoints': list(coordinates), 'scores': list(np.ones((frames, 1, 133), dtype=np.float32) * 1.1), 'w_h': [1280, 720]}


class Response(io.BytesIO):
    def __init__(self, data, start, end, total, status=206):
        super().__init__(data)
        self.status, self.headers = status, {'Content-Range': f'bytes {start}-{end}/{total}'}


class RangeTests(unittest.TestCase):
    def reader(self, payloads, **kwargs):
        parts = [{'size': len(data), 'url': f'https://huggingface.co/owner/repo/resolve/{"a" * 40}/part.{n}'} for n, data in enumerate(payloads)]
        def opener(req, timeout):
            n = int(req.full_url.split('/part.')[1].split('?')[0])
            start, end = map(int, req.headers['Range'][6:].split('-'))
            return Response(payloads[n][start:end + 1], start, end, len(payloads[n]))
        return MultipartRangeReader(parts, opener=opener, **kwargs)

    def test_seek_read_across_parts_and_cache(self):
        with self.reader([b'abcdefgh', b'ijklmnop'], block_bytes=4) as stream:
            stream.seek(6)
            self.assertEqual(stream.read(7), b'ghijklm')
            spent = stream.transferred
            stream.seek(6)
            self.assertEqual(stream.read(7), b'ghijklm')
            self.assertEqual(stream.transferred, spent)
            stream.seek(-3, 2)
            self.assertEqual(stream.read(), b'nop')
            self.assertEqual(stream.read(), b'')

    def test_transfer_budget_never_falls_back_to_full_download(self):
        with self.reader([b'1234567890'], block_bytes=4, budget_bytes=4) as stream:
            self.assertEqual(stream.read(4), b'1234')
            with self.assertRaisesRegex(ValueError, 'budget'):
                stream.read(1)

    def test_full_response_wrong_range_or_short_body_rejected(self):
        for response in (Response(b'1234', 0, 3, 4, status=200),
                         Response(b'1234', 1, 4, 4), Response(b'123', 0, 3, 4)):
            with self.reader([b'1234'], block_bytes=4) as stream:
                stream.opener = lambda *args, **kwargs: response
                with self.assertRaises(ValueError):
                    stream.read(4)

    def test_zipfile_reads_multipart_and_checks_member_crc(self):
        buf = io.BytesIO()
        with ZipFile(buf, 'w') as archive:
            archive.writestr('pose.pkl', b'known numeric bytes')
        data = buf.getvalue()
        with self.reader([data[:41], data[41:]], block_bytes=16) as stream:
            with ZipFile(stream) as archive:
                self.assertEqual(archive.read('pose.pkl'), b'known numeric bytes')

    def test_mutable_or_nonpublisher_urls_rejected(self):
        for url in ('http://huggingface.co/a/b/resolve/' + 'a' * 40 + '/part',
                    'https://huggingface.co/a/b/resolve/main/part', 'https://example.com/part'):
            with self.assertRaises(ValueError):
                MultipartRangeReader([{'size': 1, 'url': url}])


class PreparationTests(unittest.TestCase):
    def convert(self, data=None, split='train'):
        return convert_publisher_pose(pickle.dumps(numeric_pose() if data is None else data, protocol=4),
                                      name='video000001_1-1-rgb_front', text='Hello.', split=split)

    def test_full_frame_order_without_fabricated_timestamps_or_score_clamping(self):
        sample = self.convert(numeric_pose(610))
        self.assertEqual(sample.features.shape, (610, 399))
        self.assertEqual(sample.frame_indices.tolist(), list(range(610)))
        self.assertIsNone(sample.timestamps_ms)
        self.assertGreater(float(sample.features[0, 2]), 1)
        source, target = unisign_collate([sample])
        self.assertEqual(source['attention_mask'].sum(), 610)
        self.assertEqual(target['gt_sentence'], ['Hello.'])

    def test_publisher_frame_interval_is_honored_without_extra_random_crop(self):
        pose = numeric_pose(30) | {'start': 2, 'end': 29}
        sample = self.convert(pose)
        self.assertEqual(sample.frame_indices.tolist(), list(range(2, 29)))
        self.assertEqual(len(sample.features), 27)

    def test_nonfinite_multiple_signers_empty_and_invalid_interval_rejected(self):
        bad = []
        data = numeric_pose(); data['scores'][0][0, 1] = np.nan; bad.append(data)
        data = numeric_pose(); data['keypoints'] = np.zeros((20, 2, 133, 2)); bad.append(data)
        bad.extend([numeric_pose(0), numeric_pose() | {'start': 3, 'end': 2}])
        for data in bad:
            with self.assertRaises(ValueError): self.convert(data)

    def test_arbitrary_pickle_globals_are_not_executed(self):
        import os
        with self.assertRaisesRegex(ValueError, 'global'):
            convert_publisher_pose(pickle.dumps(os.system), name='a', text='Hello.', split='train')

    def test_selection_matches_train_directory_and_has_distinct_source_groups(self):
        labels = {}; members = []
        for group in ('video000001', 'video000002', 'video000003'):
            for clip in (1, 2):
                key = f'{group}_{clip}-1-rgb_front.mp4'
                labels[key] = {'text': 'Hello.'}
                members.append({'path': 'train-pose-rtmpose-192/' + key.replace('.mp4', '.pkl'), 'bytes': 5000})
                members.append({'path': 'test-pose-rtmpose-192/' + key.replace('.mp4', '.pkl'), 'bytes': 5000})
        first = select_pilot(labels, members, count=2, excluded_groups=['video000001'])
        self.assertEqual(first, select_pilot(labels, list(reversed(members)), count=2, excluded_groups=['video000001']))
        self.assertEqual({source_group(key) for key, _ in first}, {'video000002', 'video000003'})
        self.assertTrue(all(member['path'].startswith('train-') for _, member in first))
        with self.assertRaises(ValueError): select_pilot(labels, members, count=4)
        with self.assertRaises(ValueError): select_pilot(labels, members + [members[0]], count=2)

    def test_joined_sentence_ids_keep_same_source_group(self):
        self.assertEqual(source_group('video000001_2_3_4-5-rgb_front.mp4'), 'video000001')
        with self.assertRaises(ValueError): source_group('../video000001.mp4')

    def test_annotation_file_is_strict_text_dictionary(self):
        key = 'video000001_1-1-rgb_front.mp4'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'labels.gz'
            path.write_bytes(gzip.compress(pickle.dumps({key: {'name': key, 'video_path': key, 'text': 'Hello.'}})))
            self.assertEqual(len(load_publisher_labels(path)), 1)
            path.write_bytes(gzip.compress(pickle.dumps({key: {'name': key, 'video_path': key, 'text': ''}})))
            with self.assertRaises(ValueError): load_publisher_labels(path)

    def cache(self, tmp, split='train'):
        root = Path(tmp); sample = self.convert(split=split)
        numeric = save_numeric(sample, root / 'sample.npz')
        manifest = {'schema_version': 'neosignis.prepared-pose-pilot.v1', 'publisher_split': split,
                    'feature_schema': POSE_SCHEMA, 'owner_authorization_record': 'test-fixture-only',
                    'records': [{'id': sample.id, 'text': sample.text, 'publisher_split': split, 'numeric': numeric}]}
        (root / 'manifest.json').write_text(json.dumps(manifest))
        return manifest

    def test_numeric_cache_roundtrip_and_model_collation(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.cache(tmp)
            dataset = PreparedPoseDataset(tmp, split='train', usage='training')
            self.assertEqual(len(dataset), 1)
            self.assertIsNone(dataset[0].timestamps_ms)
            self.assertEqual(unisign_collate([dataset[0]])[0]['body'].shape, (1, 20, 9, 3))

    def test_validation_cache_preserves_real_irregular_pts(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = self.convert()
            times = np.cumsum(np.array([0] + [33, 41, 40, 35, 50, 38, 39, 45, 32, 40, 45, 35, 40, 40, 33, 35, 45, 40, 39], dtype=np.float64))
            val = Utterance(sample.id, sample.text, 'val', sample.features, sample.observed, times,
                            POSE_SCHEMA, 'actual-decoder-fixture.v1')
            numeric = save_numeric(val, Path(tmp) / 'val.npz')
            m = {'schema_version': 'neosignis.prepared-pose-pilot.v1', 'publisher_split': 'val',
                 'feature_schema': POSE_SCHEMA, 'extractor_version': val.extractor_version,
                 'records': [{'id': val.id, 'text': val.text, 'publisher_split': 'val', 'numeric': numeric}]}
            (Path(tmp) / 'manifest.json').write_text(json.dumps(m))
            loaded = PreparedPoseDataset(tmp, split='val', usage='evaluation')[0]
            np.testing.assert_array_equal(loaded.timestamps_ms, times)
            self.assertEqual(loaded.extractor_version, val.extractor_version)

    def test_cache_hash_change_and_validation_training_misuse_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.cache(tmp, split='val')
            with self.assertRaisesRegex(ValueError, 'Training requires'):
                PreparedPoseDataset(tmp, split='val', usage='training')
            dataset = PreparedPoseDataset(tmp, split='val')
            with (Path(tmp) / 'sample.npz').open('ab') as stream: stream.write(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash'): dataset[0]

    def test_manifest_split_mixing_and_traversal_rejected(self):
        for override in ({'publisher_split': 'val'}, {'path': '../sample.npz'}):
            with tempfile.TemporaryDirectory() as tmp:
                m = self.cache(tmp)
                if 'path' in override: m['records'][0]['numeric']['path'] = override['path']
                else: m['records'][0].update(override)
                (Path(tmp) / 'manifest.json').write_text(json.dumps(m))
                with self.assertRaises(ValueError): PreparedPoseDataset(tmp, split='train')

    def test_object_arrays_are_never_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = self.cache(tmp)
            path = Path(tmp) / 'sample.npz'
            np.savez(path, features=np.array([{}], dtype=object), observed=np.ones(1, dtype=bool), frame_indices=np.arange(1))
            m['records'][0]['numeric']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            (Path(tmp) / 'manifest.json').write_text(json.dumps(m))
            with self.assertRaises(ValueError): PreparedPoseDataset(tmp, split='train')[0]

    def test_cli_prepare_resume_reuses_verified_numeric_files_without_redownloading_members(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/data/prepare_training_pilot.py'
        spec = importlib.util.spec_from_file_location('prepare_training_pilot_test', script)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); labels = {}; buffer = io.BytesIO()
            with ZipFile(buffer, 'w') as archive:
                for group in ('video000001', 'video000002'):
                    key = group + '_1-1-rgb_front.mp4'
                    labels[key] = {'name': key, 'video_path': key, 'text': 'Hello.'}
                    archive.writestr('train-pose-rtmpose-192/' + key.replace('.mp4', '.pkl'), pickle.dumps(numeric_pose(), protocol=4))
            labels_path = root / 'labels.gz'; labels_path.write_bytes(gzip.compress(pickle.dumps(labels)))
            metadata = root / 'parts.json'
            metadata.write_text(json.dumps({'repo': module.REPO, 'revision': module.POSE_REVISION,
                                            'parts': [{'rfilename': f'how2sign_pose_format.zip.{n:02d}', 'size': 1} for n in range(4)]}))
            refs = root / 'val.csv'; refs.write_text('VIDEO_ID\nvideo000003\n')
            class FakeRange(io.BytesIO):
                transferred = 123; requests = 1; budget = 64 * 1024**2
            with patch.object(module, 'MultipartRangeReader', lambda *a, **k: FakeRange(buffer.getvalue())), \
                 patch.object(module, 'LABELS_SHA256', hashlib.sha256(labels_path.read_bytes()).hexdigest()), \
                 patch('builtins.print'):
                module.prepare(metadata, labels_path, refs, root / 'prepared', count=2)
                before = sorted(hashlib.sha256(path.read_bytes()).hexdigest() for path in (root / 'prepared').glob('*.npz'))
                with patch.object(ZipFile, 'read', side_effect=AssertionError('Resume must not read pose members again')):
                    module.prepare(metadata, labels_path, refs, root / 'prepared', count=2)
                after = sorted(hashlib.sha256(path.read_bytes()).hexdigest() for path in (root / 'prepared').glob('*.npz'))
                self.assertEqual(before, after)
                self.assertEqual(len(PreparedPoseDataset(root / 'prepared', split='train')), 2)


if __name__ == '__main__': unittest.main()
