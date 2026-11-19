"""Whole-utterance inputs and length-aware batches; no implicit truncation."""
from dataclasses import dataclass
import random

import numpy as np


@dataclass(frozen=True)
class Utterance:
    id: str
    text: str
    split: str
    features: np.ndarray  # [time, feature]; extractor-specific layout
    observed: np.ndarray  # bool [time, feature]; missing != padding
    timestamps_ms: np.ndarray  # source PTS, relative to first decoded frame
    feature_schema: str
    extractor_version: str

    def validate(self):
        if not self.id or not self.text.strip() or self.split not in {'train', 'val', 'test'}:
            raise ValueError('Utterance requires ID, text and publisher split')
        if not self.feature_schema or not self.extractor_version:
            raise ValueError('Feature schema and extractor version are required')
        if self.features.ndim != 2 or min(self.features.shape) < 1:
            raise ValueError('Expected nonempty [time, feature] array')
        if self.features.dtype != np.float32 or not np.isfinite(self.features).all():
            raise ValueError('Features must be finite float32; use observed mask for missing values')
        if self.observed.shape != self.features.shape or self.observed.dtype != np.bool_:
            raise ValueError('Observed mask must be boolean and match features')
        times = self.timestamps_ms
        if times.ndim != 1 or len(times) != len(self.features) or not np.isfinite(times).all():
            raise ValueError('Timestamps must be finite and match frame count')
        if times[0] != 0 or (np.diff(times) <= 0).any():
            raise ValueError('Timestamps must start at zero and strictly increase')
        return self


def collate_utterances(samples, *, max_padded_frames=7200, max_batch_bytes=256 * 1024**2,
                       encode_text=None, max_target_tokens=512):
    """Pad to batch maximum. True frame_mask means data, not padding.

    Text remains whole. Tokenization belongs to the selected model adapter;
    do not impose an unrelated tokenizer's length limit here.
    """
    if not samples:
        raise ValueError('Cannot collate an empty batch')
    for sample in samples:
        sample.validate()
    signatures = {(s.feature_schema, s.extractor_version, s.features.shape[1]) for s in samples}
    if len(signatures) != 1 or len({s.split for s in samples}) != 1:
        raise ValueError('Do not mix feature layouts, extractors or dataset splits')
    if len({s.id for s in samples}) != len(samples):
        raise ValueError('Duplicate utterance IDs in batch')
    lengths = np.array([len(s.features) for s in samples], dtype=np.int64)
    batch, longest, width = len(samples), int(lengths.max()), samples[0].features.shape[1]
    # float32 features + bool observed + float64 timestamps + bool frame mask.
    padded = batch * longest
    if padded > max_padded_frames or padded * (width * 5 + 9) > max_batch_bytes:
        raise ValueError('Batch exceeds memory/frame budget; use smaller length buckets, not truncation')
    features = np.zeros((batch, longest, width), dtype=np.float32)
    observed = np.zeros(features.shape, dtype=np.bool_)
    timestamps = np.zeros((batch, longest), dtype=np.float64)
    frame_mask = np.zeros((batch, longest), dtype=np.bool_)
    for index, sample in enumerate(samples):
        count = len(sample.features)
        features[index, :count] = np.where(sample.observed, sample.features, 0)
        observed[index, :count] = sample.observed
        timestamps[index, :count] = sample.timestamps_ms
        frame_mask[index, :count] = True
    result = {'ids': [s.id for s in samples], 'texts': [s.text for s in samples],
            'split': samples[0].split, 'features': features, 'observed': observed,
            'timestamps_ms': timestamps, 'frame_mask': frame_mask, 'lengths': lengths,
            'feature_schema': samples[0].feature_schema, 'extractor_version': samples[0].extractor_version}
    if encode_text is not None:
        # The adapter supplies a frozen tokenizer with truncation disabled,
        # including its EOS/special-token convention. No tokenizer downloads.
        tokens = [list(encode_text(s.text)) for s in samples]
        if any(not ids or len(ids) > max_target_tokens
               or any(isinstance(i, bool) or not isinstance(i, (int, np.integer)) or i < 0 for i in ids)
               for ids in tokens):
            raise ValueError('Invalid/oversized target tokens; full text must not be silently truncated')
        longest_target = max(map(len, tokens))
        if padded * (width * 5 + 9) + batch * longest_target * 9 > max_batch_bytes:
            raise ValueError('Targets exceed combined batch memory budget')
        labels = np.full((batch, longest_target), -100, dtype=np.int64)
        target_mask = np.zeros(labels.shape, dtype=np.bool_)
        for index, ids in enumerate(tokens):
            labels[index, :len(ids)] = ids
            target_mask[index, :len(ids)] = True
        result.update(labels=labels, target_mask=target_mask)
    return result


def torch_collate_utterances(samples, **kwargs):
    """Optional PyTorch DataLoader collate_fn; torch is not an API dependency."""
    import torch
    batch = collate_utterances(samples, **kwargs)
    return {key: torch.from_numpy(value) if isinstance(value, np.ndarray) else value
            for key, value in batch.items()}


class LengthBucketSampler:
    """Indices for DataLoader(batch_sampler=...), using actual feature lengths.

    Every sample appears once per epoch. No drop_last, splitting or replacement.
    The frame budget includes padding, rather than just summed true lengths.
    """
    def __init__(self, lengths, *, max_batch_size=4, max_padded_frames=7200, seed=0, shuffle=True):
        lengths = list(lengths)
        if (any(isinstance(n, bool) or not isinstance(n, int) or n < 1
                for n in (max_batch_size, max_padded_frames)) or not lengths
                or any(isinstance(n, bool) or not isinstance(n, (int, np.integer))
                       or n < 1 or n > max_padded_frames for n in lengths)):
            raise ValueError('Invalid lengths/budget; oversized samples cannot be silently dropped')
        self.lengths = lengths
        self.max_batch_size, self.max_padded_frames = max_batch_size, max_padded_frames
        self.seed, self.shuffle, self.epoch = seed, shuffle, 0

    def set_epoch(self, epoch):
        self.epoch = epoch

    def _batches(self):
        rng = random.Random(self.seed + self.epoch)
        indices = list(range(len(self.lengths)))
        if self.shuffle:
            rng.shuffle(indices)
        indices.sort(key=lambda i: self.lengths[i])
        batches, current = [], []
        for index in indices:
            if current and (len(current) == self.max_batch_size
                            or (len(current) + 1) * self.lengths[index] > self.max_padded_frames):
                batches.append(current)
                current = []
            current.append(index)
        if current:
            batches.append(current)
        if self.shuffle:
            rng.shuffle(batches)
        return batches

    def __iter__(self):
        return iter(self._batches())

    def __len__(self):
        return len(self._batches())
