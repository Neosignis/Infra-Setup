"""Lazy, integrity-pinned How2Sign ZIP input. Never recut sentence clips by CSV START.

    START/END refer to source recordings, not offsets inside sentence MP4s.
    A real, versioned extractor must be supplied for model features.
"""
import csv
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import stat
from zipfile import ZipFile

import numpy as np

from .utterances import Utterance


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Clip:
    id: str
    member: str
    text: str
    reference_start_s: float
    reference_end_s: float
    bytes: int
    sha256: str


class How2SignArchive:
    """Map-style records and sequential native-frame decoding, without extraction.

    A new ZIP handle is opened for every iteration, safe for DataLoader workers.
    Default usage is inspection. Training requires publisher train split plus an
    externally maintained approval record; this class does not grant data rights.
    """
    def __init__(self, archive, inventory, references, *, split, usage='inspection',
                 approval_record_id=None, max_clip_bytes=64 * 1024**2,
                 max_frames=7200, max_duration_s=120, max_feature_bytes=64 * 1024**2):
        if split not in {'train', 'val', 'test'} or usage not in {'inspection', 'evaluation', 'training'}:
            raise ValueError('Explicit publisher split and valid usage are required')
        if usage == 'training' and (split != 'train' or not approval_record_id):
            raise ValueError('Training requires publisher train split and a data approval record')
        if (any(isinstance(n, bool) or not isinstance(n, int) or n <= 0
                for n in (max_clip_bytes, max_frames, max_feature_bytes))
                or not math.isfinite(max_duration_s) or max_duration_s <= 0):
            raise ValueError('Resource bounds must be positive')
        self.archive = Path(archive)
        self.split, self.usage, self.approval_record_id = split, usage, approval_record_id
        self.max_clip_bytes, self.max_frames = max_clip_bytes, max_frames
        self.max_duration_s, self.max_feature_bytes = max_duration_s, max_feature_bytes
        checked = json.loads(Path(inventory).read_text())
        self.archive_sha256 = sha256_file(self.archive)
        if self.archive_sha256 != checked['archive_sha256']:
            raise ValueError('Source archive differs from checked inventory')
        self.references_sha256 = sha256_file(references)
        rows = {}
        with Path(references).open(newline='', encoding='utf-8-sig') as source:
            for row in csv.DictReader(source, delimiter='\t'):
                name = row['SENTENCE_NAME']
                start, end = float(row['START']), float(row['END'])
                if (not name or name in rows or not row['SENTENCE'].strip()
                        or not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start):
                    raise ValueError('Invalid/duplicate reference ID, text or interval')
                rows[name] = row
        videos = {}
        for entry in checked['entries']:
            if not entry['is_mp4']:
                continue
            member = PurePosixPath(entry['path'])
            if member.is_absolute() or '..' in member.parts or '\\' in entry['path'] or member.stem in videos:
                raise ValueError('Unsafe member path or duplicate video ID')
            videos[member.stem] = entry
        self.missing_video_ids = sorted(set(rows) - set(videos))
        self.unreferenced_video_ids = sorted(set(videos) - set(rows))
        self.records = tuple(Clip(name, videos[name]['path'], rows[name]['SENTENCE'],
                                  float(rows[name]['START']), float(rows[name]['END']),
                                  videos[name]['bytes'], videos[name]['sha256'])
                             for name in sorted(set(rows) & set(videos)))
        if not self.records:
            raise ValueError('No matched clips')

    def __len__(self):
        return len(self.records)

    def iter_frames(self, index):
        """Yield (relative PTS in ms, original AV frame), all frames or an error.

        Consumers doing sequential inspection must exhaust the iterator before
        claiming whole-clip success. No fixed-FPS assumption or silent skipping.
        """
        import av
        clip = self.records[index]
        with ZipFile(self.archive) as archive:
            matches = [info for info in archive.infolist() if info.filename == clip.member]
            if len(matches) != 1:
                raise ValueError('Missing/duplicate archive member')
            info = matches[0]
            mode = info.external_attr >> 16
            if (stat.S_ISLNK(mode) or info.flag_bits & 1 or info.file_size != clip.bytes
                    or not 0 < info.file_size <= self.max_clip_bytes):
                raise ValueError('Unsafe/oversized clip or changed member size')
            payload = archive.read(info)
        if hashlib.sha256(payload).hexdigest() != clip.sha256:
            raise ValueError('Clip hash differs from checked inventory')
        with av.open(io.BytesIO(payload), format='mov', options={'enable_drefs': '0'}) as container:
            if len(container.streams.video) != 1:
                raise ValueError('Expected exactly one video stream')
            stream = container.streams.video[0]
            stream.codec_context.thread_count = 1
            origin, previous, dimensions, count = None, None, None, 0
            for count, frame in enumerate(container.decode(video=0), start=1):
                if count > self.max_frames:
                    raise ValueError('Frame budget exceeded; utterance was not truncated into a valid sample')
                if not (0 < frame.width <= 4096 and 0 < frame.height <= 4096):
                    raise ValueError('Unsupported dimensions')
                if dimensions is not None and dimensions != (frame.width, frame.height):
                    raise ValueError('Frame dimensions changed')
                dimensions = (frame.width, frame.height)
                if frame.time is None or not math.isfinite(frame.time):
                    raise ValueError('Missing/nonfinite PTS; cannot assume source FPS')
                timestamp = float(frame.time)
                if previous is not None and timestamp <= previous:
                    raise ValueError('Nonincreasing PTS')
                if origin is None:
                    origin = timestamp
                if timestamp - origin > self.max_duration_s:
                    raise ValueError('Duration budget exceeded; complete sample rejected')
                previous = timestamp
                yield (timestamp - origin) * 1000, frame
            if count == 0:
                raise ValueError('Video decoded no frames')

    def load(self, index, extractor, *, feature_schema, extractor_version):
        """extractor(AVFrame) -> (flat float features, boolean observation mask).

        Frame processing is incremental; RGB sequences are never accumulated.
        Extractor owns color/layout/normalization and must declare its version.
        No part of this loader fabricates poses or translations.
        """
        times, features, masks, total_bytes, width = [], [], [], 0, None
        for timestamp, frame in self.iter_frames(index):
            values, mask = extractor(frame)
            values, mask = np.asarray(values, dtype=np.float32), np.asarray(mask)
            if values.ndim != 1 or not values.size or mask.shape != values.shape or mask.dtype != np.bool_:
                raise ValueError('Extractor must return feature vector and matching boolean mask')
            if not np.isfinite(values).all() or width not in (None, len(values)):
                raise ValueError('Nonfinite features or changing feature layout')
            width = len(values)
            total_bytes += values.nbytes + mask.nbytes + 8
            # Lists plus final stacked arrays coexist briefly: reserve twice.
            if total_bytes * 2 > self.max_feature_bytes:
                raise ValueError('Feature memory budget exceeded; complete sample rejected')
            times.append(timestamp)
            features.append(values.copy())
            masks.append(mask.copy())
        clip = self.records[index]
        return Utterance(clip.id, clip.text, self.split, np.stack(features), np.stack(masks),
                         np.asarray(times, dtype=np.float64), feature_schema, extractor_version).validate()


class FeatureDataset:
    """PyTorch map-style compatible wrapper; no framework import is required."""
    def __init__(self, source, extractor, *, feature_schema, extractor_version):
        self.source, self.extractor = source, extractor
        self.feature_schema, self.extractor_version = feature_schema, extractor_version

    def __len__(self):
        return len(self.source)

    def __getitem__(self, index):
        return self.source.load(index, self.extractor, feature_schema=self.feature_schema,
                                extractor_version=self.extractor_version)
