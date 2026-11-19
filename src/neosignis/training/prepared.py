"""Numeric pose pilot datasets, with explicit split and timing provenance."""
from dataclasses import dataclass
import gzip
import hashlib
import io
import json
import pickle
from pathlib import Path, PurePosixPath
import re

import numpy as np

from .how2sign import sha256_file
from .pose import POSE_SCHEMA, CONFIDENCE_THRESHOLD, unisign_parts
from .utterances import Utterance

PUBLISHER_EXTRACTOR = 'unisign.publisher.rtmpose.frame-indexed.v1'


class _DataUnpickler(pickle.Unpickler):
    def __init__(self, file, *, arrays=False):
        super().__init__(file)
        self.arrays = arrays

    def find_class(self, module, name):
        # These are only permitted for the pinned publisher's numeric pose
        # files, never a public upload endpoint or arbitrary user pickle.
        if self.arrays:
            allowed = {
                ('numpy', 'ndarray'): np.ndarray,
                ('numpy', 'dtype'): np.dtype,
                ('numpy.core.multiarray', '_reconstruct'): np.core.multiarray._reconstruct,
                ('numpy.core.multiarray', 'scalar'): np.core.multiarray.scalar,
            }
            if (module, name) in allowed:
                return allowed[module, name]
        raise ValueError('Serialized data requested an unsupported global')

    def persistent_load(self, pid):
        raise ValueError('External serialized references are prohibited')


def source_group(name):
    match = re.fullmatch(r'([A-Za-z0-9_-]{11})_\d+(?:_\d+)*-\d+-rgb_front(?:\.mp4|\.pkl)?', name)
    if not match:
        raise ValueError('Unrecognized How2Sign frontal sentence ID')
    return match[1]


def load_publisher_labels(path):
    """Upstream gzip/pickle annotation dictionaries: no globals permitted."""
    with gzip.open(path, 'rb') as stream:
        payload = stream.read(16 * 1024**2 + 1)
    if len(payload) > 16 * 1024**2:
        raise ValueError('Annotations exceed 16 MiB bound')
    data = _DataUnpickler(io.BytesIO(payload)).load()
    if type(data) is not dict or not 1 <= len(data) <= 100000:
        raise ValueError('Expected bounded annotation dictionary')
    for key, item in data.items():
        if (type(key) is not str or type(item) is not dict or item.get('name') != key
                or item.get('video_path') != key or not key.endswith('.mp4')
                or type(item.get('text')) is not str or not item['text'].strip()
                or len(item['text']) > 10000):
            raise ValueError('Invalid publisher annotation')
        source_group(key)
    return data


def select_pilot(labels, members, *, count=32, excluded_groups=(), split='train'):
    """Select deterministically across source videos, without relabelling splits."""
    if type(count) is not int or not 1 <= count <= 256 or split not in {'train', 'val', 'test'}:
        raise ValueError('Pilot selection must be 1..256')
    excluded = set(excluded_groups)
    available = {}
    for member in members:
        path = PurePosixPath(member['path'])
        if path.is_absolute() or '..' in path.parts or '\\' in member['path']:
            raise ValueError('Unsafe publisher member path')
        if path.suffix != '.pkl' or member['bytes'] < 1000 or member['bytes'] > 32 * 1024**2:
            continue
        if path.parts[0] != f'{split}-pose-rtmpose-192':
            continue
        key = path.stem + '.mp4'
        if key not in labels or source_group(key) in excluded:
            continue
        if key in available:
            raise ValueError('Ambiguous pose member for annotation')
        available[key] = member
    def order(key):
        return hashlib.sha256(('neosignis-pilot-v1:' + key).encode()).hexdigest()
    # One complete utterance per source video in this small process pilot.
    selected, groups = [], set()
    for key in sorted(available, key=order):
        group = source_group(key)
        if group in groups:
            continue
        selected.append((key, available[key])); groups.add(group)
        if len(selected) == count:
            break
    if len(selected) < count:
        raise ValueError('Not enough distinct matching source groups for pilot')
    return selected


@dataclass(frozen=True)
class IndexedPoseUtterance:
    id: str
    text: str
    split: str
    features: np.ndarray
    observed: np.ndarray
    frame_indices: np.ndarray
    feature_schema: str = POSE_SCHEMA
    extractor_version: str = PUBLISHER_EXTRACTOR
    timestamps_ms: None = None

    def validate(self):
        if (not self.id or not self.text.strip() or self.split not in {'train', 'val', 'test'}
                or self.feature_schema != POSE_SCHEMA or not self.extractor_version):
            raise ValueError('Invalid frame-indexed pose metadata')
        if (self.features.ndim != 2 or self.features.shape[1] != 399
                or not 1 <= len(self.features) <= 7200 or self.features.dtype != np.float32
                or not np.isfinite(self.features).all()):
            raise ValueError('Invalid numeric pose sequence')
        if (self.observed.shape != self.features.shape or self.observed.dtype != np.bool_
                or self.frame_indices.dtype != np.int64 or self.frame_indices.shape != (len(self.features),)
                or self.frame_indices[0] < 0 or np.any(np.diff(self.frame_indices) != 1)
                or self.timestamps_ms is not None):
            raise ValueError('Invalid observation or source-frame order; do not fabricate timestamps')
        return self


def convert_publisher_pose(payload, *, name, text, split):
    """Retain every declared frame; no fixed FPS, resampling or random clipping."""
    if not 0 < len(payload) <= 32 * 1024**2:
        raise ValueError('Publisher pose exceeds byte bound')
    data = _DataUnpickler(io.BytesIO(payload), arrays=True).load()
    if type(data) is not dict or not {'keypoints', 'scores'} <= data.keys():
        raise ValueError('Expected publisher keypoints and scores')
    coordinates, scores = np.asarray(data['keypoints']), np.asarray(data['scores'])
    if (coordinates.dtype.kind not in 'fi' or scores.dtype.kind not in 'fi'
            or coordinates.ndim != 4 or coordinates.shape[1:] != (1, 133, 2)
            or scores.shape != coordinates.shape[:-1] or not 1 <= len(scores) <= 7200
            or not np.isfinite(coordinates).all() or not np.isfinite(scores).all()):
        raise ValueError('Expected finite single-signer COCO133 publisher pose arrays')
    start, end = data.get('start', 0), data.get('end', len(scores))
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(scores):
        raise ValueError('Invalid publisher frame interval')
    # Publisher extraction code divides x/y by frame width/height. Preserve
    # this normalized layout and raw scores; do not invent FPS or timestamps.
    raw = np.concatenate([coordinates[start:end, 0], scores[start:end, 0, :, None]], axis=-1).astype(np.float32)
    mask = np.repeat((raw[:, :, 2] > CONFIDENCE_THRESHOLD)[:, :, None], 3, axis=2)
    result = IndexedPoseUtterance(name, text, split, raw.reshape(-1, 399), mask.reshape(-1, 399),
                                  np.arange(start, end, dtype=np.int64)).validate()
    unisign_parts(result)  # Reject degenerate/incompatible geometry before cache publication.
    return result


def save_numeric(sample, path):
    sample.validate()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ValueError('Refusing to overwrite prepared numeric file')
    with path.open('xb') as stream:
        clock = ({'timestamps_ms': sample.timestamps_ms} if sample.timestamps_ms is not None
                 else {'frame_indices': sample.frame_indices})
        np.savez_compressed(stream, features=sample.features, observed=sample.observed, **clock)
    return {'path': path.name, 'sha256': sha256_file(path), 'bytes': path.stat().st_size,
            'frames': len(sample.features), 'timestamps': ('source_pts_ms' if sample.timestamps_ms is not None
                                                          else 'unavailable_source_frame_order_only')}


class PreparedPoseDataset:
    """Map-style, non-pickle numeric input for the existing Uni-Sign collator."""
    def __init__(self, root, *, split, usage='inspection'):
        self.root = Path(root).resolve()
        self.manifest = json.loads((self.root / 'manifest.json').read_text())
        if (self.manifest['schema_version'] != 'neosignis.prepared-pose-pilot.v1'
                or split != self.manifest['publisher_split'] or split not in {'train', 'val', 'test'}
                or usage not in {'inspection', 'evaluation', 'training'}):
            raise ValueError('Invalid manifest, usage or publisher split')
        if usage == 'training' and (split != 'train' or not self.manifest.get('owner_authorization_record')):
            raise ValueError('Training requires publisher train data and recorded authorization')
        if self.manifest.get('feature_schema') != POSE_SCHEMA:
            raise ValueError('Incompatible pose layout')
        self.records = self.manifest['records']
        if not self.records or len({r['id'] for r in self.records}) != len(self.records):
            raise ValueError('Empty/duplicate prepared records')
        for record in self.records:
            path = PurePosixPath(record['numeric']['path'])
            if (path.is_absolute() or '..' in path.parts or '\\' in str(path)
                    or record['publisher_split'] != split):
                raise ValueError('Unsafe path or split mixing')
            if record.get('extractor_version', self.manifest.get('extractor_version', PUBLISHER_EXTRACTOR)) != self.manifest.get('extractor_version', PUBLISHER_EXTRACTOR):
                raise ValueError('Mixed pose extractor versions')

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        record = self.records[index]
        path = (self.root / record['numeric']['path']).resolve()
        if not path.is_relative_to(self.root) or path.stat().st_size > 32 * 1024**2:
            raise ValueError('Numeric file escaped cache or exceeded bound')
        if sha256_file(path) != record['numeric']['sha256']:
            raise ValueError('Prepared numeric file hash mismatch')
        # NPZ numeric arrays only; pickle/object arrays are never loaded.
        from zipfile import ZipFile
        with ZipFile(path) as archive:
            if sum(f.file_size for f in archive.infolist()) > 32 * 1024**2:
                raise ValueError('Expanded numeric cache exceeds bound')
        with np.load(path, allow_pickle=False) as arrays:
            clock = record['numeric']['timestamps']
            time_field = 'timestamps_ms' if clock == 'source_pts_ms' else 'frame_indices'
            if clock not in {'source_pts_ms', 'unavailable_source_frame_order_only'} or set(arrays.files) != {'features', 'observed', time_field}:
                raise ValueError('Unexpected numeric fields')
            if time_field == 'timestamps_ms':
                sample = Utterance(record['id'], record['text'], self.manifest['publisher_split'],
                                   arrays['features'], arrays['observed'], arrays['timestamps_ms'],
                                   POSE_SCHEMA, self.manifest['extractor_version'])
            else:
                sample = IndexedPoseUtterance(record['id'], record['text'], self.manifest['publisher_split'],
                                             arrays['features'], arrays['observed'], arrays['frame_indices'])
        sample.validate()
        if len(sample.features) != record['numeric']['frames']:
            raise ValueError('Prepared length changed')
        return sample
