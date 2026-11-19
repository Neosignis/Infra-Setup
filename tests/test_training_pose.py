import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

from neosignis.training.pose import (
    POSE_SCHEMA, DetectedSignerPredictor, WholeBodyFrameExtractor, unisign_parts, unisign_collate, torch_unisign_collate,
)
from neosignis.training.utterances import Utterance
from neosignis.training.checkpoint import load_tensor_checkpoint, restore_model


def pose_sample(name='sample', length=4):
    raw = np.empty((length, 133, 3), dtype=np.float32)
    raw[:, :, :2], raw[:, :, 2] = .5, .9
    raw[:, 0, :2], raw[:, 3, :2] = .25, .75
    raw[:, 92, :2] = [.625, .375]
    raw[:, 113, :2] = [.375, .625]
    raw[:, 23, :2] = [.75, .5]
    return Utterance(name, 'Complete reference sentence.', 'val', raw.reshape(length, 399),
                     np.ones((length, 399), dtype=np.bool_), np.arange(length, dtype=np.float64) * 40,
                     POSE_SCHEMA, 'synthetic.coco133.v1')


class Frame:
    width, height = 200, 100

    def to_ndarray(self, *, format):
        if format != 'bgr24':
            raise AssertionError('Predictor expects BGR input')
        image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        image[0, 0] = [7, 11, 23]
        return image


class PoseTests(unittest.TestCase):
    def test_predictor_gets_bgr_and_pixels_become_normalized_xy(self):
        def predictor(image):
            self.assertEqual(image[0, 0].tolist(), [7, 11, 23])
            return np.tile([100, 25], (1, 133, 1)), np.full((1, 133), .9)
        values, mask = WholeBodyFrameExtractor(predictor, version='test')(Frame())
        np.testing.assert_allclose(values.reshape(133, 3)[0], [.5, .25, .9])
        self.assertTrue(mask.all())
        if importlib.util.find_spec('av'):
            import av
            rgb = np.empty((100, 200, 3), dtype=np.uint8)
            rgb[:] = [23, 11, 7]
            real_frame = av.VideoFrame.from_ndarray(rgb, format='rgb24')
            real_values, real_mask = WholeBodyFrameExtractor(predictor, version='test')(real_frame)
            np.testing.assert_array_equal(values, real_values)
            np.testing.assert_array_equal(mask, real_mask)

    def test_absent_signer_stays_missing(self):
        predictor = lambda image: (np.empty((0, 133, 2)), np.empty((0, 133)))
        values, mask = WholeBodyFrameExtractor(predictor, version='test')(Frame())
        self.assertFalse(mask.any())
        self.assertFalse(values.any())

    def test_multiple_signers_and_wrong_landmark_layout_are_rejected(self):
        for count, joints in ((2, 133), (1, 553), (1, 17)):
            predictor = lambda image: (np.zeros((count, joints, 2)), np.ones((count, joints)))
            with self.assertRaisesRegex(ValueError, 'one signer'):
                WholeBodyFrameExtractor(predictor, version='test')(Frame())

    def test_invalid_prediction_values_do_not_become_valid_poses(self):
        for score in (np.nan, np.inf, -np.inf):
            predictor = lambda image: (np.zeros((1, 133, 2)), np.full((1, 133), score))
            with self.assertRaises(ValueError):
                WholeBodyFrameExtractor(predictor, version='test')(Frame())

    def test_raw_simcc_scores_above_one_are_preserved_then_model_clipped(self):
        predictor = lambda image: (np.tile([100, 25], (1, 133, 1)), np.full((1, 133), 1.5))
        values, mask = WholeBodyFrameExtractor(predictor, version='raw-simcc')(Frame())
        self.assertEqual(values.reshape(133, 3)[0, 2], 1.5)
        self.assertTrue(mask.all())
        sample = pose_sample()
        sample.features.reshape(-1, 133, 3)[:, :, 2] = 1.5
        branches, _ = unisign_parts(sample)
        self.assertEqual(branches['body'][0, 0, 2], 1)

    def test_detector_no_person_never_falls_back_to_invented_full_image_pose(self):
        calls = []
        def pose(image, *, bboxes):
            calls.append(bboxes)
            return np.zeros((1, 133, 2)), np.ones((1, 133))
        missing = DetectedSignerPredictor(lambda image: [], pose)
        self.assertEqual(missing(None)[0].shape, (0, 133, 2))
        self.assertFalse(calls)
        with self.assertRaisesRegex(ValueError, 'Multiple'):
            DetectedSignerPredictor(lambda image: [[0] * 4, [1] * 4], pose)(None)
        detected = DetectedSignerPredictor(lambda image: [[0, 0, 200, 100]], pose)
        self.assertEqual(detected(None)[0].shape, (1, 133, 2))
        self.assertEqual(len(calls), 1)

    def test_body_square_normalization_hand_anchors_and_face_indices(self):
        branches, masks = unisign_parts(pose_sample())
        self.assertEqual({k: v.shape for k, v in branches.items()},
                         {'body': (4, 9, 3), 'left': (4, 21, 3), 'right': (4, 21, 3), 'face_all': (4, 18, 3)})
        np.testing.assert_allclose(branches['body'][0, 0], [-1, -1, .9])
        np.testing.assert_allclose(branches['body'][0, 1], [1, 1, .9])
        np.testing.assert_allclose(branches['left'][0, 1], [.25, -.25, .9])
        np.testing.assert_allclose(branches['right'][0, 1], [-.25, .25, .9])
        np.testing.assert_allclose(branches['face_all'][0, 0], [.5, 0, .9])
        self.assertTrue(all(mask.all() for mask in masks.values()))

    def test_low_confidence_body_outlier_does_not_set_scale(self):
        sample = pose_sample()
        raw, observed = sample.features.reshape(-1, 133, 3), sample.observed.reshape(-1, 133, 3)
        raw[:, 4] = [1000, 1000, .1]
        observed[:, 4] = False
        branches, masks = unisign_parts(sample)
        np.testing.assert_allclose(branches['body'][0, 0], [-1, -1, .9])
        self.assertFalse(branches['body'][:, 2].any())
        self.assertFalse(masks['body'][:, 2].any())

    def test_missing_frames_remain_temporally_present(self):
        sample = pose_sample()
        sample.features[1] = 0
        sample.observed[1] = False
        source, _ = unisign_collate([sample])
        self.assertEqual(source['attention_mask'][0, 1], 1)
        self.assertFalse(source['body'][0, 1].any())

    def test_degenerate_body_and_inconsistent_masks_rejected(self):
        for case in ('missing', 'scale', 'mask'):
            sample = pose_sample()
            if case == 'missing':
                sample.features[:] = 0
                sample.observed[:] = False
            elif case == 'scale':
                sample.features.reshape(-1, 133, 3)[:, :, :2] = .5
            else:
                sample.observed[0, 0] = False
            with self.assertRaises(ValueError):
                unisign_parts(sample)

    def test_long_batch_preserves_whole_sequences_and_repeats_boundary_only_for_padding(self):
        long, short = pose_sample('long', 1704), pose_sample('short', 9)
        source, target = unisign_collate([long, short])
        self.assertEqual(source['body'].shape, (2, 1704, 9, 3))
        self.assertEqual(source['src_length_batch'].tolist(), [1704, 9])
        self.assertEqual(source['attention_mask'].sum(axis=1).tolist(), [1704, 9])
        np.testing.assert_array_equal(source['body'][1, 8], source['body'][1, -1])
        self.assertEqual(target['gt_sentence'], [long.text, short.text])
        self.assertEqual(target['gt_gloss'], ['', ''])

    def test_wrong_schema_split_and_oversize_batch_rejected(self):
        sample = pose_sample()
        object.__setattr__(sample, 'feature_schema', 'neosignis.landmarks.v1')
        with self.assertRaisesRegex(ValueError, 'COCO'):
            unisign_parts(sample)
        with self.assertRaisesRegex(ValueError, 'budget'):
            unisign_collate([pose_sample()], max_padded_frames=3)
        other = pose_sample('other')
        object.__setattr__(other, 'split', 'train')
        with self.assertRaisesRegex(ValueError, 'Mixed'):
            unisign_collate([pose_sample(), other])

    @unittest.skipUnless(importlib.util.find_spec('torch'), 'Optional PyTorch adapter')
    def test_real_torch_model_input_shapes(self):
        import torch
        source, target = torch_unisign_collate([pose_sample()])
        self.assertEqual(source['left'].dtype, torch.float32)
        self.assertEqual(source['attention_mask'].dtype, torch.int64)
        self.assertEqual(len(target['gt_sentence']), 1)


class UnsupportedObject:
    def __reduce__(self):
        return eval, ('1 + 1',)


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Optional tensor checkpoint checks')
class CheckpointTests(unittest.TestCase):
    def setUp(self):
        import torch
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'fixture.pt'
        self.model = torch.nn.Linear(3, 2)

    def save(self, value):
        import torch
        torch.save(value, self.path)
        return {'expected_sha256': hashlib.sha256(self.path.read_bytes()).hexdigest(),
                'expected_bytes': self.path.stat().st_size}

    def test_checkpoint_wrapped_and_unwrapped_state_round_trip(self):
        import torch
        for value in (self.model.state_dict(), {'model': self.model.state_dict(), 'epoch': 2}):
            expected = self.save(value)
            restored = restore_model(torch.nn.Linear(3, 2), self.path, **expected)
            torch.testing.assert_close(restored.weight, self.model.weight)

    def test_size_and_hash_mismatch_rejected_before_loading(self):
        expected = self.save(self.model.state_dict())
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            load_tensor_checkpoint(self.path, **{**expected, 'expected_sha256': '0' * 64})
        with self.assertRaisesRegex(ValueError, 'byte count'):
            load_tensor_checkpoint(self.path, **{**expected, 'expected_bytes': 1})

    def test_shape_mismatch_does_not_modify_model(self):
        import torch
        expected = self.save(torch.nn.Linear(4, 2).state_dict())
        before = self.model.weight.detach().clone()
        with self.assertRaisesRegex(ValueError, 'keys/shapes'):
            restore_model(self.model, self.path, **expected)
        torch.testing.assert_close(before, self.model.weight)

    def test_nonfinite_and_nontensor_weights_rejected(self):
        import torch
        for value in ({'weight': torch.tensor([float('nan')])}, {'weight': 'not a tensor'}):
            with self.assertRaises(ValueError):
                load_tensor_checkpoint(self.path, **self.save(value))

    def test_unrestricted_pickle_is_never_used_as_fallback(self):
        import pickle
        expected = self.save({'model': {'weight': UnsupportedObject()}})
        with self.assertRaises(pickle.UnpicklingError):
            load_tensor_checkpoint(self.path, **expected)


if __name__ == '__main__':
    unittest.main()
