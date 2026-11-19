"""Independently implemented pose-input adapter; no pretrained extractor bundled.

Numerical contract reviewed against Uni-Sign revision
eed438bcb49e30405cd6ccdfcccca330c134e830. End-to-end checkpoint parity
remains unverified. Whole-utterance normalization is an offline operation.
"""
import numpy as np

from .utterances import Utterance

POSE_SCHEMA = 'neosignis.coco133.xys.v2'  # raw finite SimCC scores, not probabilities
PARTS = {
    'body': (0, 3, 4, 5, 6, 7, 8, 9, 10),
    'left': tuple(range(91, 112)),
    'right': tuple(range(112, 133)),
    'face_all': (23, 25, 27, 29, 31, 33, 35, 37, 39, 83, 84, 85, 86, 87, 88, 89, 90, 53),
}
ANCHORS = {'left': 91, 'right': 112, 'face_all': 53}
CONFIDENCE_THRESHOLD = 0.3


def load_local_pose_extractor(root):
    """Use the same hash-checked single-person extractor for capture and data."""
    import hashlib
    import json
    from pathlib import Path
    from rtmlib import Wholebody
    assets = json.loads((Path(root) / 'pose/assets.json').read_text())
    for record in assets.values():
        if hashlib.sha256(Path(record['onnx']).read_bytes()).hexdigest() != record['onnx_sha256']:
            raise ValueError('Pose asset identity changed')
    models = Wholebody(det=assets['detector']['onnx'], det_input_size=(416, 416),
                       pose=assets['pose']['onnx'], pose_input_size=(192, 256),
                       to_openpose=False, backend='onnxruntime', device='cpu')
    return WholeBodyFrameExtractor(DetectedSignerPredictor(models.det_model, models.pose_model),
                                   version='rtmlib.0.0.13.raw-simcc-v1')


class DetectedSignerPredictor:
    """Prevent RTMLib's full-image pose fallback when detection finds no signer."""
    def __init__(self, detector, pose_model):
        self.detector, self.pose_model = detector, pose_model

    def __call__(self, image):
        boxes = self.detector(image)
        if len(boxes) == 0:
            return np.empty((0, 133, 2), dtype=np.float32), np.empty((0, 133), dtype=np.float32)
        if len(boxes) != 1:
            raise ValueError('Multiple people require explicit signer tracking')
        return self.pose_model(image, bboxes=boxes)


class WholeBodyFrameExtractor:
    """Wrap a trusted RTMLib-compatible predictor, supplied by the local caller.

    predictor(BGR uint8 image) -> pixel coordinates [people,133,2] and
    scores [people,133]. No-person frames stay missing; multiple people
    require explicit tracking rather than silently selecting the first person.
    """
    def __init__(self, predictor, *, version):
        if not callable(predictor) or not version:
            raise ValueError('A versioned whole-body predictor is required')
        self.predictor, self.version = predictor, version

    def __call__(self, frame):
        image = frame.to_ndarray(format='bgr24')
        coordinates, confidence = self.predictor(image)
        coordinates = np.asarray(coordinates, dtype=np.float32)
        confidence = np.asarray(confidence, dtype=np.float32)
        if coordinates.shape == (0, 133, 2) and confidence.shape == (0, 133):
            return np.zeros(399, dtype=np.float32), np.zeros(399, dtype=np.bool_)
        if coordinates.shape != (1, 133, 2) or confidence.shape != (1, 133):
            raise ValueError('Expected one signer in COCO WholeBody 133 layout')
        if not np.isfinite(coordinates).all() or not np.isfinite(confidence).all():
            raise ValueError('Nonfinite pose prediction')
        # RTMPose returns raw SimCC peak responses. Values above one (and
        # negative missing observations) are possible; these are not calibrated
        # probabilities. Preserve them until checkpoint-specific conversion.
        values = np.empty((133, 3), dtype=np.float32)
        values[:, :2] = coordinates[0] / np.array([frame.width, frame.height], dtype=np.float32)
        values[:, 2] = confidence[0]
        mask = np.repeat((confidence[0] > CONFIDENCE_THRESHOLD)[:, None], 3, axis=1)
        return values.reshape(-1), mask.reshape(-1)


def unisign_parts(sample):
    """Convert raw x/y/score features to body/hand/face model branches.

    Retains every source frame. Low-confidence joints become zero, while
    temporal validity remains separate. Degenerate body scale is rejected.
    """
    sample.validate()
    if sample.feature_schema != POSE_SCHEMA or sample.features.shape[1] != 399:
        raise ValueError('Expected versioned COCO WholeBody 133 x/y/score features')
    raw = sample.features.reshape(-1, 133, 3)
    scores = raw[:, :, 2]
    expected_mask = np.repeat((scores > CONFIDENCE_THRESHOLD)[:, :, None], 3, axis=2)
    if not np.array_equal(sample.observed.reshape(raw.shape), expected_mask):
        raise ValueError('Observation mask must agree with the pinned confidence convention')
    body = raw[:, PARTS['body'], :]
    valid_body = body[:, :, 2] > CONFIDENCE_THRESHOLD
    visible_coordinates = body[:, :, :2][valid_body]
    if len(visible_coordinates) < 4:
        raise ValueError('Insufficient body observations for whole-utterance normalization')
    lower = visible_coordinates.min(axis=0)
    upper = visible_coordinates.max(axis=0)
    scale = float((upper - lower).max())
    if scale <= 0:
        raise ValueError('Degenerate body scale')
    center = (upper + lower) / 2
    branches, joint_masks = {}, {}
    for name, indices in PARTS.items():
        points = raw[:, indices, :].copy()
        if name == 'body':
            points[:, :, :2] = (points[:, :, :2] - center) * (2 / scale)
        else:
            anchor = raw[:, ANCHORS[name], :2]
            points[:, :, :2] = (points[:, :, :2] - anchor[:, None, :]) / scale
        valid = points[:, :, 2] > CONFIDENCE_THRESHOLD
        np.clip(points, -1, 1, out=points)
        points[~valid] = 0
        branches[name] = points
        joint_masks[name] = valid
    return branches, joint_masks


def unisign_collate(samples, *, max_padded_frames=7200):
    """Pose-only model input: repeat final frames for padding, mask them out.

    Upstream temporal convolutions see repeated boundary values, so generic
    zero padding is not substituted here. The model must consume the mask.
    """
    if not samples:
        raise ValueError('Empty pose batch')
    if len({(s.split, s.feature_schema, s.extractor_version) for s in samples}) != 1:
        raise ValueError('Mixed dataset splits or extractor versions')
    if len({s.id for s in samples}) != len(samples):
        raise ValueError('Duplicate utterance IDs')
    longest = max(len(s.features) for s in samples)
    if len(samples) * longest > max_padded_frames:
        raise ValueError('Padded frame budget exceeded; do not truncate utterances')
    converted = [unisign_parts(sample) for sample in samples]
    source = {part: np.empty((len(samples), longest, len(indices), 3), dtype=np.float32)
              for part, indices in PARTS.items()}
    attention = np.zeros((len(samples), longest), dtype=np.int64)
    lengths = np.array([len(s.features) for s in samples], dtype=np.int64)
    for index, (branches, _masks) in enumerate(converted):
        count = int(lengths[index])
        attention[index, :count] = 1
        for part, values in branches.items():
            source[part][index, :count] = values
            source[part][index, count:] = values[-1]
    source.update(attention_mask=attention, src_length_batch=lengths,
                  name_batch=[s.id for s in samples])
    target = {'gt_sentence': [s.text for s in samples], 'gt_gloss': [''] * len(samples)}
    return source, target


def torch_unisign_collate(samples, **kwargs):
    import torch
    source, target = unisign_collate(samples, **kwargs)
    return {k: torch.from_numpy(v) if isinstance(v, np.ndarray) else v
            for k, v in source.items()}, target
